// Package idgentest provides a canned Generator for deterministic tests.
package idgentest

import (
	"sync"

	"example.com/neo/service/pkg/idgen"
)

// Stub is a Generator that returns caller-supplied ids in order, cycling back to
// the start when exhausted (and a constant "stub-id" when none were supplied).
// This makes the request / idempotency ids emitted by the code under test
// assertable. Safe for concurrent use — the document background task generates
// its id on a separate goroutine.
type Stub struct {
	mu  sync.Mutex
	ids []string
	i   int
}

// NewStub constructs a Stub that yields ids in order (cycling). With no ids it
// yields a constant "stub-id".
func NewStub(ids ...string) *Stub { return &Stub{ids: ids} }

// NewString returns the next canned id.
func (s *Stub) NewString() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.ids) == 0 {
		return "stub-id"
	}
	id := s.ids[s.i%len(s.ids)]
	s.i++
	return id
}

// Compile-time interface check — fails compilation if Stub drifts from Generator.
var _ idgen.Generator = (*Stub)(nil)
