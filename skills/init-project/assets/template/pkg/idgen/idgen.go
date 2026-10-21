// Package idgen provides an injectable identifier generator so that request /
// idempotency ids can be fixed deterministically in tests. Production code wires
// System() (UUIDv7); tests wire a canned generator (see idgentest.Stub).
package idgen

import "github.com/google/uuid"

// Generator produces unique string identifiers. Inject it wherever business
// logic would otherwise call uuid.NewString() directly, so the produced id can
// be asserted in tests.
type Generator interface {
	NewString() string
}

// uuidGenerator is the production Generator; it produces a time-ordered UUIDv7 string.
type uuidGenerator struct{}

func (uuidGenerator) NewString() string { return uuid.Must(uuid.NewV7()).String() }

// System returns the production Generator backed by uuid.NewV7().
func System() Generator { return uuidGenerator{} }
