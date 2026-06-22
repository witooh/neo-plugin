package config

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
	"time"

	"github.com/go-viper/mapstructure/v2"
	"gopkg.in/yaml.v3"

	"example.com/neo/service/internal/adapters/repository/redis"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/logger"
)

var Conf Config

// Config is the typed runtime configuration. A freshly scaffolded service wires
// only the infrastructure every service needs (logger, HTTP, Postgres, Redis,
// Kafka). neo adds an upstream sub-struct here per integration it introduces
// (see .kiro/steering/app.md + integration.md).
type Config struct {
	LoggerConfig   logger.Config  `mapstructure:"logger"`
	ServiceConfig  ServiceConfig  `mapstructure:"service"`
	PostgresConfig PostgresConfig `mapstructure:"postgres"`
	RedisConfig    redis.Config   `mapstructure:"redis"`
	KafkaConfig    KafkaConfig    `mapstructure:"kafka"`
}

type ServiceConfig struct {
	Host            string        `mapstructure:"host"`
	Port            string        `mapstructure:"port"`
	ShutdownTimeout time.Duration `mapstructure:"shutdown_timeout"`
	ServiceId       string        `mapstructure:"service_id"`
}

type PostgresConfig struct {
	Host     string `mapstructure:"host"`
	Port     int    `mapstructure:"port"`
	User     string `mapstructure:"user"`
	Password string `mapstructure:"password"`
	Database string `mapstructure:"database"`
	SSLMode  string `mapstructure:"sslmode"`
	Schema   string `mapstructure:"schema"`
}

type KafkaConfig struct {
	Enabled       bool   `mapstructure:"enabled"`
	Address       string `mapstructure:"address"`
	UseAwsProfile bool   `mapstructure:"use_aws_profile"`
}

func init() {
	if testing.Testing() {
		return
	}
	if err := load(&Conf); err != nil {
		panic(fmt.Errorf("fatal error config: %w", err))
	}
}

// load reads the YAML config file, overlays environment-variable overrides, and
// decodes the result into out. Environment variables win over file values and are
// keyed by the dotted path in upper snake case (postgres.host -> POSTGRES_HOST);
// SIT/production inject the full config this way from the secret manager.
func load(out *Config) error {
	raw, err := os.ReadFile(configFilePath())
	if err != nil {
		return err
	}

	var fileMap map[string]any
	if err := yaml.Unmarshal(raw, &fileMap); err != nil {
		return err
	}
	overlayEnv(fileMap, "")

	decoder, err := mapstructure.NewDecoder(&mapstructure.DecoderConfig{
		Result:           out,
		WeaklyTypedInput: true,
		DecodeHook: mapstructure.ComposeDecodeHookFunc(
			mapstructure.TextUnmarshallerHookFunc(),
			mapstructure.StringToTimeDurationHookFunc(),
			mapstructure.StringToSliceHookFunc(","),
		),
	})
	if err != nil {
		return err
	}
	return decoder.Decode(fileMap)
}

// configFilePath resolves the single config file, preferring the working-directory
// copy (the path used inside the container) and falling back to the file sitting
// next to this source (config/config.yaml) for local `go run`/`go test` invocations.
func configFilePath() string {
	if _, err := os.Stat("./config/config.yaml"); err == nil {
		return "./config/config.yaml"
	}
	_, b, _, _ := runtime.Caller(0)
	return filepath.Join(filepath.Dir(b), "config.yaml")
}

// overlayEnv walks the parsed config map and replaces every leaf whose upper
// snake-case dotted path is set as an environment variable, mutating m in place.
func overlayEnv(m map[string]any, prefix string) {
	for key, val := range m {
		path := key
		if prefix != "" {
			path = prefix + "_" + key
		}
		if child, ok := val.(map[string]any); ok {
			overlayEnv(child, path)
			continue
		}
		if env, ok := os.LookupEnv(strings.ToUpper(path)); ok {
			m[key] = env
		}
	}
}

// ConnectionString returns the PostgreSQL connection string.
// The format is: postgres://username:password@host:port/database?sslmode=sslmode
// Example: postgres://username:password@localhost:5432/mydb?sslmode=disable
func (p *PostgresConfig) ConnectionString() string {
	return fmt.Sprintf("postgres://%s:%s@%s:%d/%s?sslmode=%s",
		p.User,
		p.Password,
		p.Host,
		p.Port,
		p.Database,
		p.SSLMode,
	)
}
