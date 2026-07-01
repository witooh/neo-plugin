package kafka

import (
	"context"
	"encoding/json"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/ory/dockertest/v3"
	"github.com/ory/dockertest/v3/docker"
	"github.com/segmentio/kafka-go"
	"github.com/stretchr/testify/require"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/ctxutils"
)

type Int int

func (a Int) Marshal() ([]byte, error) {
	return json.Marshal(a)
}

func (a *Int) Unmarshal(data []byte) error {
	return json.Unmarshal(data, a)
}
func TestKafka(t *testing.T) {
	if testing.Short() {
		t.Skip("Kafka tests skipped in short mode")
	}
	kafkaPort := "59092" // Fix port

	pool, err := dockertest.NewPool("")
	if err != nil {
		t.Fatal(err)
	}
	if err = pool.Client.Ping(); err != nil {
		t.Fatalf("Could not connect to Docker: %s", err)
	}
	resource, err := pool.RunWithOptions(&dockertest.RunOptions{
		Repository: "apache/kafka",
		Tag:        "4.1.0",
		Env: []string{
			"KAFKA_NODE_ID=1",
			"KAFKA_PROCESS_ROLES=broker,controller",
			"KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093",
			"KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093",
			"KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:" + kafkaPort,
			"KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT",
			"KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER",
			"KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1",
			"KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1",
			"KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1",
			"KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS=0",
			"KAFKA_NUM_PARTITIONS=3",
		},
		ExposedPorts: []string{
			"9092/tcp",
		},
		PortBindings: map[docker.Port][]docker.PortBinding{
			"9092/tcp": {
				{
					HostIP:   "0.0.0.0",
					HostPort: kafkaPort,
				},
			},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	defer func() {
		if err := pool.Purge(resource); err != nil {
			t.Fatalf("Could not purge resource: %s", err)
		}

	}()
	kafkaAddress := "localhost:" + kafkaPort

	if err := pool.Retry(func() error {
		conn, err := kafka.Dial("tcp", kafkaAddress)
		if err != nil {
			return err
		}

		if err := conn.CreateTopics(kafka.TopicConfig{
			Topic:             "test",
			NumPartitions:     3,
			ReplicationFactor: 1,
		}); err != nil {
			return err
		}
		return nil
	}); err != nil {
		t.Fatal(err)
	}

	t.Run("Producer", func(t *testing.T) {
		ctx := context.Background()
		ctx = context.WithValue(ctx, ctxutils.ContextKey_CorrelationId{}, uuid.NewString())
		producer, err := NewProducer[Int](ctx, &KafkaProducerConfig{
			Address: kafkaAddress,
			Topic:   "test",
			Async:   false,
		})
		if err != nil {
			t.Fatal(err)
		}
		defer producer.Close()
		for i := 1; i <= 10; i++ {
			if err := producer.Produce(ctx, uuid.New().String(), Int(i)); err != nil {
				t.Fatal(err)
			}
		}
	})

	t.Run("Consumer", func(t *testing.T) {
		ctx := context.Background()
		consumer, err := NewConsumer[Int](ctx, &KafkaConsumerConfig{
			Address: kafkaAddress,
			GroupId: "my-group",
			Topic:   "test",
		})
		if err != nil {
			t.Fatal(err)
		}
		defer consumer.Close()
		ch := consumer.Consume(ctx)

		msgCount := 0
		timer := time.NewTimer(10 * time.Second)
	OUTER:
		for {
			select {
			case <-timer.C:
				t.Fatalf("time limit exceeded")
			case msg, ok := <-ch:
				require.True(t, ok, "channel is closed")
				t.Logf("Received message: %d", msg.Data)
				msgCount++
				if err := consumer.Commit(ctx, msg); err != nil {
					t.Log("error when committing messages to kafka", err)
					continue
				}
				if msgCount == 10 {
					break OUTER
				}
			}
		}
	})
}
