---
inclusion: fileMatch
fileMatchPattern: "**/internal/delivery/consumer/**,**/internal/adapters/eventbus/**,**/pkg/messaging/**"
---

# Messaging (Kafka inbound + outbound)

Two directions, plus a shared contract:

- **Inbound** — `internal/delivery/consumer`: receive events, route them to usecases.
- **Outbound** — `internal/adapters/eventbus`: publish domain events (implements the
  `<context>.EventPublisher` port, co-located in `internal/core/domain/<context>`).
- **Infra** — `internal/adapters/eventbus/kafka`: shared client glue (producer/consumer).
- **Contract** — `pkg/messaging`: the wire contract both directions share — `eventid`
  (routing ids), `models` (Avro transport models), `schema` (`.avsc`). It lives in `pkg/`
  so inbound (delivery) and outbound (adapter) both import it without crossing layers.

```
internal/delivery/consumer/
    processor.go         # owns an inbound port + routes by event id → usecase.Exec
internal/adapters/eventbus/
    eventbus.go          # ProducerAdapter / ConsumerAdapter + New…Adapter (over the kafka producer/consumer)
    kafka/
        producer/        # low-level produce
        consumer/        # low-level consume loop
pkg/messaging/           # wire contract shared by inbound + outbound (imported by both, crosses no layer)
    eventid/             # ProcessingTopic / SuccessTopic enums + routing ids
    models/              # Avro / transport models (generated; regen from schema/)
    schema/              # .avsc schema definitions (regen source)
```

## Inbound — processor (driving adapter)

The processor is a **driving adapter**: it owns a small inbound port (the usecase
contract it needs), decodes the transport payload into a local DTO, and dispatches by
event id. It does **not** import the usecase package — it depends on the port
structurally, so any matching `Exec` satisfies it.

```go
// Package consumer routes inbound events to usecases. Transport DTOs only; no business logic.
package consumer

// <Thing>Upserter is the driving port into the <thing> use case (satisfied structurally).
type <Thing>Upserter interface {
	Exec(ctx context.Context, /* domain inputs */) error
}

type processor struct {
	<Thing>s <Thing>Upserter
}

func New(u <Thing>Upserter) *processor { return &processor{<Thing>s: u} }

func (p *processor) Process(ctx context.Context, msg *kafka.KafkaMessage[models.<Event>]) error {
	switch eventid.ProcessingTopic(msg.Data.EventID) {
	case eventid.ProcessingTopic_<Case>:
		return p.handle<Case>(ctx, msg.Data.Data)
	default:
		logger.Debug("ignoring event", logger.String("eventId", msg.Data.EventID))
		return nil
	}
}

func (p *processor) handle<Case>(ctx context.Context, data []byte) error {
	var dto <Case>Data
	if err := json.Unmarshal(data, &dto); err != nil {
		return err
	}
	return p.<Thing>s.Exec(ctx, /* ... */)
}
```

> When a usecase method that the processor calls is renamed, the **processor's own port
> method and the call site must change in the same commit** — the structural match
> breaks the instant the names diverge.

### Transport DTOs

Structs mirroring the upstream event payload (with `json`/Avro tags) live in the
consumer (or `pkg/messaging/models`). Map them to domain inputs before calling the
usecase; never pass a transport DTO into `domain`.

## Outbound — publisher

Satisfies the `<context>.EventPublisher` port structurally — the usecase depends on the port
(co-located in `internal/core/domain/<context>`); the composition root injects this adapter. Unlike the
gateway/repository constructors that return their port interface, the producer constructor
returns its concrete adapter type (`ProducerAdapter`) and an error:

```go
func NewProducerAdapter(ctx context.Context, cfg *producer.Config) (ProducerAdapter, error) { /* ... */ }
```

Publish **domain events** (from the owning context's `events.go`, e.g.
`<context>.<Aggregate>Opened`) mapped to the wire model. Keep the published contract stable — it is
an API.

## Semantics

- **At-least-once.** `Process` must be **idempotent**: the same event may be delivered
  twice. Dedupe by a natural key or an idempotency check in the usecase.
- Returning an error from `Process` triggers redelivery; returning `nil` commits the
  offset. Skip-and-commit (`return nil`) for events this service does not handle.
- `eventid` enums are the single source of routing truth — add a case there + in `Process`.

## Don'ts

- ✗ Business logic in the processor — decode, route, delegate.
- ✗ Importing the usecase package into the consumer (depend on the inbound port instead).
- ✗ Failing the whole batch on an unknown event id — skip it.
