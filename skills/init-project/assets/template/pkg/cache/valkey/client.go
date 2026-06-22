package valkey

import (
	"context"
	"crypto/tls"
	"errors"
	"fmt"
	"time"

	"github.com/redis/go-redis/v9"
)

// Tight per-operation deadlines keep a slow Valkey from dominating the
// 100ms total request budget (overview.md §4 NFR table). Values target
// in-datacenter Valkey; a real outage hits these limits and the caller
// surfaces a 503 fast instead of timing out the consumer.
const (
	dialTimeout  = 200 * time.Millisecond
	readTimeout  = 50 * time.Millisecond
	writeTimeout = 50 * time.Millisecond
)

// Client is the read/write contract used by cache adapters.
type Client interface {
	Get(ctx context.Context, key string) ([]byte, error)
	Set(ctx context.Context, key string, value []byte, ttl time.Duration) error
	Delete(ctx context.Context, key string) error
	Close() error
}

type Config struct {
	Addr      string
	Username  string
	Password  string
	Database  int
	UseTLS    bool
	KeyPrefix string // required; the caller's cache namespace, e.g. "user:" — must be non-empty
}

var ErrNotFound = errors.New("valkey: key not found")

type client struct {
	rdb       *redis.Client
	keyPrefix string
}

// NewClient constructs a Valkey-backed cache client. The underlying
// go-redis client lazily dials on first command, so this constructor
// never blocks on network I/O.
//
// An empty cfg.KeyPrefix is a wiring error (every cache user must declare
// its namespace) and panics here rather than at first command — this
// surfaces the misconfiguration at startup, not in production traffic.
func NewClient(cfg Config) Client {
	if cfg.KeyPrefix == "" {
		panic("valkey.NewClient: Config.KeyPrefix must be non-empty")
	}
	opts := &redis.Options{
		Addr:         cfg.Addr,
		Username:     cfg.Username,
		Password:     cfg.Password,
		DB:           cfg.Database,
		DialTimeout:  dialTimeout,
		ReadTimeout:  readTimeout,
		WriteTimeout: writeTimeout,
	}
	if cfg.UseTLS {
		// MinVersion 1.2 baseline; default verification uses system roots
		// and the hostname embedded in cfg.Addr — sufficient for ElastiCache
		// which serves a publicly-rooted certificate.
		opts.TLSConfig = &tls.Config{MinVersion: tls.VersionTLS12}
	}
	return &client{rdb: redis.NewClient(opts), keyPrefix: cfg.KeyPrefix}
}

func (c *client) Get(ctx context.Context, key string) ([]byte, error) {
	b, err := c.rdb.Get(ctx, c.namespaced(key)).Bytes()
	if errors.Is(err, redis.Nil) {
		return nil, ErrNotFound
	}
	if err != nil {
		return nil, fmt.Errorf("valkey get %q: %w", key, err)
	}
	return b, nil
}

func (c *client) Set(ctx context.Context, key string, value []byte, ttl time.Duration) error {
	if err := c.rdb.Set(ctx, c.namespaced(key), value, ttl).Err(); err != nil {
		return fmt.Errorf("valkey set %q: %w", key, err)
	}
	return nil
}

func (c *client) Delete(ctx context.Context, key string) error {
	if err := c.rdb.Del(ctx, c.namespaced(key)).Err(); err != nil {
		return fmt.Errorf("valkey delete %q: %w", key, err)
	}
	return nil
}

func (c *client) Close() error { return c.rdb.Close() }

// namespaced returns the storage key with this client's prefix applied.
func (c *client) namespaced(key string) string { return c.keyPrefix + key }
