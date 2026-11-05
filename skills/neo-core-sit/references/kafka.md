# Kafka: topics, offsets and payloads for SIT and UAT

One recipe for Core and Auxiliary, SIT and UAT, through the Kafbat UI REST API. Use it to check whether
an event reached a topic, read its payload, or see whether a consumer group keeps up.
The shared cluster inspection procedure owns the permission rule; this file is only the Kafka recipe.
Use only the active skill's bindings: never a SIT URL for a UAT question, or the reverse.

Measured on 2026-11-05 with Kafbat v1.5.0 in all four environments. Messages were read back on Core SIT,
Core UAT and Auxiliary UAT. Every Auxiliary SIT topic then had `offsetMax` 0 and returned an empty `DONE`,
so that one payload path stays unproven until a message exists.

## Rules

- **GET only, even when asked.** That rules out a produce, a topic delete and an offset reset. This recipe
  has no write path: tell the user what change is needed and leave the Kafbat UI step to them.
- **Payloads can hold customer data.** Print only what the question needs, and never write one to repo
  files, skills or durable memory. Drop `value` from the filter when offsets or keys are enough;
  `email-gateway-send-v1` values reach 79 KB on Auxiliary UAT. On UAT, keep `value`, `key` and header
  values out of reports unless the user asked for that message.
- **Use Kafbat, not a direct broker.** Brokers use `SASL_SSL` with `AWS_MSK_IAM` on port 9098. That port
  connected from the laptop only on Auxiliary UAT and no direct read was tried, so do not reach for `kcat`
  or `kafka-console-consumer`.

Reads left no consumer group behind in any environment. Expect Kafbat to need the VPN: its hostnames resolve
to private addresses.

## Confirm the target

Use `KAFBAT_URL`, `KAFKA_CLUSTER` and `KAFKA_BROKER` from the active skill.

```bash
curl -s -m 15 "$KAFBAT_URL/api/clusters/$KAFKA_CLUSTER/brokers" | jq -r '.[].host'
```

Every host must contain `KAFKA_BROKER`; otherwise stop. A hostname's address does not identify the Kafka:
`core.uat` and `auxiliary.uat` resolve to the same addresses yet serve different brokers.

To re-check `KAFKA_BROKER` itself, ask AWS after the shared procedure's gate, with the wrapper's `DOMAIN`:

```bash
ARN="$(aws kafka list-clusters-v2 --profile "$PROFILE" --region "$REGION" \
  --query "ClusterInfoList[?contains(ClusterName, '$DOMAIN')].ClusterArn" --output text)"
aws kafka get-bootstrap-brokers --cluster-arn "$ARN" --profile "$PROFILE" --region "$REGION" \
  --query BootstrapBrokerStringSaslIam --output text
```

Then check that this is the Kafka the service uses:

- On SIT, its secret holds the broker in `.kafka.address`, on the secret path from the shared procedure §6.
  UAT wrappers set no `SECRET_PREFIX`, so there find the topic in the list below instead.
- A service can use another cluster: `sit/core/payment-gateway` also has `.kafka.aux-address`, which is on
  Auxiliary.
- No Kafbat lists a `kafka-data-hub-*` MSK cluster (Core SIT and Core UAT each have one), so events there
  cannot be read this way.
- On SIT, topic names can be in the secret too (`.kafka.success_topic`, `.kafka.error_topic` for payment).
  Key names differ by service.

## Did the event reach the topic?

```bash
curl -s -m 20 "$KAFBAT_URL/api/clusters/$KAFKA_CLUSTER/topics?perPage=500" | jq -r '.topics[].name'
curl -s -m 15 "$KAFBAT_URL/api/clusters/$KAFKA_CLUSTER/topics/$TOPIC" \
  | jq -c '.partitions[] | {partition, offsetMin, offsetMax}'
```

Record `offsetMax` on every partition, ask the user to trigger the event, then read it again. For an
event that already happened, go to finding one event below.

| Result | Meaning | Next |
|---|---|---|
| `offsetMax` rose | A message reached the topic | Read it below, then check the consumer group |
| `offsetMax` did not move | Nothing reached this topic in that window | Producer logs (shared procedure §4 or OpenSearch); compare the topic name with the secret |
| `offsetMax` is 0 everywhere | Nothing was written since the topic was created | Same. Low SIT traffic also looks like this, so it alone proves no bug |
| `offsetMin` equals `offsetMax`, above 0 | Written, then expired or deleted | The message is gone; use producer logs |
| HTTP 404 | No such topic | Compare the topic name with the secret |

## Read messages

```bash
curl -s -N -m 30 "$KAFBAT_URL/api/clusters/$KAFKA_CLUSTER/topics/$TOPIC/messages/v2?mode=LATEST&limit=3" \
  | sed -n 's/^data: *//p' \
  | jq -c 'if .type=="MESSAGE" then .message | {partition, offset, timestamp, key, headers, value}
           elif .type=="DONE" then {consumed: .consuming.messagesConsumed, cursor: .cursor.id}
           else empty end'
```

| Need | Query |
|---|---|
| Newest messages | `mode=LATEST&limit=<n>` |
| Oldest retained | `mode=EARLIEST&limit=<n>` |
| From a time | `mode=FROM_TIMESTAMP&timestamp=<epoch ms>&limit=<n>` |
| From an offset | `mode=FROM_OFFSET&offset=<n>&partitions=<p>&limit=<n>` |
| One partition | add `partitions=<p>` |
| Next page | `cursor=<id from the last line>`, with no other parameter |

- **Keep `limit` at 500 or below.** 500 returned 500, while 1000 and 5000 silently returned 100.
- **No `consumed` line means the request failed.** An invalid mode returns 400 and a missing topic 404, and
  this pipeline prints nothing for either. Rerun with `curl -i` to see which.
- **A scan is complete only when `cursor` is null.** Otherwise more messages remain, so a miss proves nothing.
  Scans followed to a null `cursor` summed to the retained count on Core and Auxiliary UAT.
- **The payload field is `value`, not `content`.** The deployed image tag is `latest`, so if a field reads
  null, check `.message | keys` before believing it.

## Find one event

`FROM_MS` is the search start in epoch milliseconds, and `CID` is the id you are looking for:

```bash
FROM_MS=$(( $(date -u -j -f '%Y-%m-%dT%H:%M:%S' "$FROM_UTC" +%s) * 1000 ))
curl -s -N -m 60 "$KAFBAT_URL/api/clusters/$KAFKA_CLUSTER/topics/$TOPIC/messages/v2?mode=FROM_TIMESTAMP&timestamp=$FROM_MS&limit=500" \
  | sed -n 's/^data: *//p' \
  | jq -c --arg cid "$CID" 'if .type=="MESSAGE" then .message | select(.headers["x-correlation-id"]==$cid) | {partition, offset, timestamp, key}
           elif .type=="DONE" then {consumed: .consuming.messagesConsumed, cursor: .cursor.id}
           else empty end'
```

`FROM_UTC` looks like `2026-11-04T08:00:00`; `date -j` is the macOS form. Follow `cursor` until it is null,
then report a miss as "not found in N messages since <time>". Stop early and it is "not found in the N read".

Headers differ by topic, so check `.message.headers | keys` first, and match `.key` when the id is the message
key. On UAT `ekyc-completed-yblzrf0dwv` carries `X-Message-Id`, `channelId` and `user`, while
`email-gateway-send-v1` and `txn-statement-request-completed` carry none.

## Consumer groups

```bash
curl -s -m 15 "$KAFBAT_URL/api/clusters/$KAFKA_CLUSTER/topics/$TOPIC/consumer-groups" \
  | jq -c '.[] | {groupId, state, members, consumerLag}'
curl -s -m 15 "$KAFBAT_URL/api/clusters/$KAFKA_CLUSTER/consumer-groups/$GROUP" \
  | jq -c '{state, members, consumerLag, partitions: [.partitions[] | {topic, partition, currentOffset, endOffset, consumerLag}]}'
```

`consumerLag` returned a number on groups with committed offsets (0 on `neotxn-payment-consumer`, Core UAT)
and `null` on groups whose topics never held a message (Core SIT), so `null` does not mean zero lag. No group
listed, or `EMPTY` with 0 members, means no consumer is attached right now.
