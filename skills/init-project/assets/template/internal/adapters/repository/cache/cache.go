// Package cache provides a key-value cache backed by Valkey/Redis.
package cache

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
)

// Cache defines generic key-value cache operations.
type Cache interface {
	Get(ctx context.Context, key string) ([]byte, error)
	Set(ctx context.Context, key string, value []byte, ttl time.Duration) error
	Del(ctx context.Context, key string) error
}

type Config struct {
	Host     string `mapstructure:"host"`
	Port     string `mapstructure:"port"`
	Username string `mapstructure:"username"`
	Password string `mapstructure:"password"`
	Database int    `mapstructure:"database"`
	UseTls   bool   `mapstructure:"use_tls"`
}

type cache struct {
	client *redis.Client
}

// NewCache creates a Cache backed by Valkey/Redis.
func NewCache(client *redis.Client) Cache {
	return &cache{client: client}
}

func (c *cache) Get(ctx context.Context, key string) ([]byte, error) {
	val, err := c.client.Get(ctx, key).Bytes()
	if err == redis.Nil {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return val, nil
}

func (c *cache) Set(ctx context.Context, key string, value []byte, ttl time.Duration) error {
	return c.client.Set(ctx, key, value, ttl).Err()
}

func (c *cache) Del(ctx context.Context, key string) error {
	return c.client.Del(ctx, key).Err()
}
