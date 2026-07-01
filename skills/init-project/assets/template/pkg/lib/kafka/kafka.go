package kafka

import "github.com/aws/aws-sdk-go-v2/aws"

type KafkaOption struct {
	Logger    KafkaLogger
	IsTesting bool
	AwsConfig *aws.Config
}

type KafkaOptionFunc func(opt *KafkaOption)

func WithLogger(logger KafkaLogger) KafkaOptionFunc {
	return func(opt *KafkaOption) {
		opt.Logger = logger
	}
}

func WithAwsConfig(c *aws.Config) KafkaOptionFunc {
	return func(opt *KafkaOption) {
		opt.AwsConfig = c
	}
}

type KafkaLogger interface {
	Info(msg string, args ...any)
	Error(msg string, args ...any)
}

type noOpLogger struct{}

func (l *noOpLogger) Info(msg string, args ...any)  {}
func (l *noOpLogger) Error(msg string, args ...any) {}

type kafkaLogger struct {
	logger KafkaLogger
}

func (l *kafkaLogger) Printf(msg string, args ...interface{}) {
	l.logger.Info(msg, args...)
}

type kafkaErrorLogger struct {
	logger KafkaLogger
}

func (l *kafkaErrorLogger) Printf(msg string, args ...interface{}) {
	l.logger.Error(msg, args...)
}
