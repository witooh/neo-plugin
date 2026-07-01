package kafka

import (
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"time"

	"github.com/cockroachdb/errors"
	kafka "github.com/segmentio/kafka-go"
	"github.com/segmentio/kafka-go/sasl/aws_msk_iam_v2"
)

type KafkaUnmarshaler[T any] interface {
	Unmarshal(b []byte) error
	*T
}
type KafkaConsumerConfig struct {
	Address       string `mapstructure:"address"`
	GroupId       string `mapstructure:"group_id"`
	Topic         string `mapstructure:"topic"`
	QueueCapacity int    `mapstructure:"queue_capacity"`
	MinBytes      int    `mapstructure:"min_bytes"`
	MaxBytes      int    `mapstructure:"max_bytes"`
}

type KafkaConsumer[T any, PT KafkaUnmarshaler[T]] struct {
	reader *kafka.Reader
	logger KafkaLogger
}

type KafkaMessage[T any] struct {
	MsgID      string
	Data       T
	RawMessage *kafka.Message
}

func (c *KafkaConsumer[T, PT]) Consume(ctx context.Context) <-chan *KafkaMessage[T] {
	ch := make(chan *KafkaMessage[T])
	go func() {
		for {
			select {
			case <-ctx.Done():
				close(ch)
				c.logger.Info("consumer stopped: %s", ctx.Err().Error())
				return
			default:
				msg, err := c.reader.FetchMessage(ctx)
				if err != nil {
					if errors.Is(err, io.EOF) {
						close(ch)
						c.logger.Error("reader has been closed: %s", err.Error())
						return
					}
					c.logger.Error("error while consuming message: %s", err.Error())
					// time.Sleep(time.Second * 5) // TODO: should be configurable
					continue
				}
				var data T
				p := PT(&data)
				if err := p.Unmarshal(msg.Value); err != nil {
					close(ch)
					c.logger.Error("parsing message data error: %s", err.Error())
					return
				}
				ch <- &KafkaMessage[T]{
					MsgID:      string(msg.Key),
					Data:       data,
					RawMessage: &msg,
				}
			}
		}
	}()

	return ch
}

func (c *KafkaConsumer[T, PT]) Commit(ctx context.Context, msg *KafkaMessage[T]) error {
	return c.reader.CommitMessages(ctx, *msg.RawMessage)
}

func (c *KafkaConsumer[T, PT]) Close() error {
	return c.reader.Close()
}

func NewConsumer[T any, PT KafkaUnmarshaler[T]](ctx context.Context, config *KafkaConsumerConfig, optFunctions ...KafkaOptionFunc) (*KafkaConsumer[T, PT], error) {
	opt := &KafkaOption{}
	for _, f := range optFunctions {
		f(opt)
	}
	if opt.Logger == nil {
		opt.Logger = &noOpLogger{}
	}

	dialer := kafka.Dialer{
		Timeout:   10 * time.Second,
		DualStack: true,
	}

	if opt.AwsConfig != nil {
		mechanism := aws_msk_iam_v2.NewMechanism(*opt.AwsConfig)
		tlsConfig := &tls.Config{} // TODO: fix tls later
		dialer.SASLMechanism = mechanism
		dialer.TLS = tlsConfig
	}

	conn, err := dialer.DialContext(ctx, "tcp", config.Address)
	if err != nil {
		return nil, errors.WithStack(err)
	}
	defer conn.Close()
	brokers, err := conn.Brokers()
	if err != nil {
		return nil, errors.WithStack(err)
	}
	partitions, err := conn.ReadPartitions(config.Topic)
	if err != nil {
		return nil, errors.WithStack(err)
	}
	if len(partitions) == 0 {
		return nil, errors.New("topic not found")
	}

	rawReader := kafka.NewReader(kafka.ReaderConfig{
		Brokers: func() []string {
			var ret []string
			for _, broker := range brokers {
				ret = append(ret, fmt.Sprintf("%s:%d", broker.Host, broker.Port))
			}
			return ret
		}(),
		Dialer:        &dialer,
		GroupID:       config.GroupId,
		Topic:         config.Topic,
		MinBytes:      config.MinBytes,
		MaxBytes:      config.MaxBytes,
		QueueCapacity: config.QueueCapacity,
		Logger: &kafkaLogger{
			logger: opt.Logger,
		},
		ErrorLogger: &kafkaErrorLogger{
			logger: opt.Logger,
		},
	})

	return &KafkaConsumer[T, PT]{
		reader: rawReader,
		logger: opt.Logger,
	}, nil
}
