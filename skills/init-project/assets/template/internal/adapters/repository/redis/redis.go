package redis

import (
	"context"
	"crypto/tls"
	"time"

	"github.com/redis/go-redis/v9"
	"github.com/redis/go-redis/v9/maintnotifications"
)

type Config struct {
	Host      string        `mapstructure:"host"`
	Port      string        `mapstructure:"port"`
	Username  string        `mapstructure:"username"`
	Password  string        `mapstructure:"password"`
	Database  int           `mapstructure:"database"`
	UseTls    bool          `mapstructure:"use_tls"`
	CSDataTTL time.Duration `mapstructure:"cs_data_ttl"` // default 30s
}

func NewClient(ctx context.Context, config *Config) (*redis.Client, error) {
	redisOption := &redis.Options{
		Addr:     config.Host + ":" + config.Port,
		Username: config.Username,
		Password: config.Password,
		DB:       config.Database,
		MaintNotificationsConfig: &maintnotifications.Config{
			Mode: maintnotifications.ModeDisabled,
		},
	}
	if config.UseTls {
		redisOption.TLSConfig = &tls.Config{ // TODO: set proper tls config
			InsecureSkipVerify: true,
		}
	}
	rdb := redis.NewClient(redisOption)
	if err := rdb.Ping(ctx).Err(); err != nil {
		return nil, err
	}
	return rdb, nil
}
