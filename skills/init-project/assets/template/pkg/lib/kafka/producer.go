package kafka

import (
	"context"
	"crypto/tls"
	"fmt"
	"net"
	"time"

	"github.com/cockroachdb/errors"
	"github.com/segmentio/kafka-go"
	"github.com/segmentio/kafka-go/sasl/aws_msk_iam_v2"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/ctxutils"
)

type KafkaProducerConfig struct {
	Address string `mapstructure:"address"`
	Topic   string `mapstructure:"topic"`
	Async   bool   `mapstructure:"async"`
}

type KafkaMarshaler[T any] interface {
	Marshal() ([]byte, error)
	*T
}
type KafkaProducer[T any, PT KafkaMarshaler[T]] struct {
	writer *kafka.Writer
}

func PrepareHeaders(keyValue map[string][]byte) []kafka.Header {
	headers := make([]kafka.Header, 0, len(keyValue))
	for k, v := range keyValue {
		headers = append(headers, kafka.Header{
			Key:   k,
			Value: v,
		})
	}
	return headers
}

func (p *KafkaProducer[T, PT]) Produce(ctx context.Context, msgID string, data T) error {
	correlationId, err := ctxutils.GetCorrelationId(ctx)
	if err != nil {
		return err
	}
	headers := PrepareHeaders(
		map[string][]byte{"x-correlation-id": []byte(correlationId)},
	)
	d := PT(&data)
	val, err := d.Marshal()
	if err != nil {
		return err
	}
	return p.writer.WriteMessages(ctx, kafka.Message{
		Key:     []byte(msgID),
		Value:   val,
		Headers: headers,
	})
}

func (p *KafkaProducer[T, PT]) Close() error {
	return p.writer.Close()
}

func NewProducer[T any, PT KafkaMarshaler[T]](ctx context.Context, config *KafkaProducerConfig, optFunctions ...KafkaOptionFunc) (*KafkaProducer[T, PT], error) {
	opt := &KafkaOption{}
	for _, f := range optFunctions {
		f(opt)
	}
	if opt.Logger == nil {
		opt.Logger = &noOpLogger{}
	}

	transport := &kafka.Transport{
		Dial: (&net.Dialer{
			Timeout:   3 * time.Second,
			DualStack: true,
		}).DialContext,
	}

	dialer := kafka.Dialer{
		Timeout:   10 * time.Second,
		DualStack: true,
	}

	if opt.AwsConfig != nil {
		mechanism := aws_msk_iam_v2.NewMechanism(*opt.AwsConfig)
		tlsConfig := &tls.Config{} // TODO: fix tls later
		transport.SASL = mechanism
		transport.TLS = tlsConfig
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

	writer := &kafka.Writer{
		Addr: kafka.TCP(func() []string {
			var ret []string
			for _, broker := range brokers {
				ret = append(ret, fmt.Sprintf("%s:%d", broker.Host, broker.Port))
			}
			return ret
		}()...),
		Transport: transport,
		Topic:     config.Topic,
		Logger: &kafkaLogger{
			logger: opt.Logger,
		},
		ErrorLogger: &kafkaErrorLogger{
			logger: opt.Logger,
		},
		Async:        config.Async,
		RequiredAcks: kafka.RequireOne,
	}

	return &KafkaProducer[T, PT]{
		writer: writer,
	}, nil
}
