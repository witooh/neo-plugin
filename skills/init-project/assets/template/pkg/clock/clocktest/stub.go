// Package clocktest provides a fixed-time Clock for deterministic tests.
package clocktest

import (
	"time"

	"example.com/neo/service/pkg/clock"
)

// Stub is a Clock that always returns a fixed instant, so time-dependent logic
// (age checks, maturity dates, campaign windows) is deterministic under test.
type Stub struct{ t time.Time }

// NewStub constructs a Stub pinned to t.
func NewStub(t time.Time) *Stub { return &Stub{t: t} }

// Now returns the fixed instant.
func (s *Stub) Now() time.Time { return s.t }

// Compile-time interface check — fails compilation if Stub drifts from Clock.
var _ clock.Clock = (*Stub)(nil)
