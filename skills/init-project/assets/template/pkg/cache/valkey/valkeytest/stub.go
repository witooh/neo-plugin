package valkeytest

import (
	"context"
	"errors"
	"sync"
	"sync/atomic"
	"time"

	"example.com/neo/service/pkg/cache/valkey"
)

var ErrStubTransport = errors.New("valkeytest: simulated transport failure")

type Stub struct {
	mu        sync.Mutex
	store     map[string][]byte
	getCalls  atomic.Int64
	setCalls  atomic.Int64
	deleteCnt atomic.Int64
	getErrFn  func(key string) error // injectable per-call GET error; nil = honour store
	setErrFn  func(key string) error // injectable per-call SET error; nil = honour store
}

// NewStub constructs a Stub backed by an empty in-memory store.
func NewStub() *Stub {
	return &Stub{store: map[string][]byte{}}
}

func (s *Stub) Preload(key string, value []byte) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.store[key] = value
}

func (s *Stub) FailGet(err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err == nil {
		s.getErrFn = nil
		return
	}
	s.getErrFn = func(_ string) error { return err }
}

func (s *Stub) FailSet(err error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if err == nil {
		s.setErrFn = nil
		return
	}
	s.setErrFn = func(_ string) error { return err }
}

// GetCalls returns the number of Get invocations observed.
func (s *Stub) GetCalls() int64 { return s.getCalls.Load() }

// SetCalls returns the number of Set invocations observed.
func (s *Stub) SetCalls() int64 { return s.setCalls.Load() }

// Peek returns the in-memory value at the given key without incrementing the
// Get counter. Useful for round-trip assertions on the cached payload.
func (s *Stub) Peek(key string) ([]byte, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	v, ok := s.store[key]
	return v, ok
}

// Get satisfies valkey.Client. It increments the call counter, then either
// returns an injected error, or reads from the store, or returns ErrNotFound.
func (s *Stub) Get(_ context.Context, key string) ([]byte, error) {
	s.getCalls.Add(1)
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.getErrFn != nil {
		if err := s.getErrFn(key); err != nil {
			return nil, err
		}
	}
	if v, ok := s.store[key]; ok {
		return v, nil
	}
	return nil, valkey.ErrNotFound
}

// Set satisfies valkey.Client. The TTL is accepted but not retained — tests
// assert TTL behaviour at the production-client integration level
// (pkg/cache/valkey/client_test.go).
func (s *Stub) Set(_ context.Context, key string, value []byte, _ time.Duration) error {
	s.setCalls.Add(1)
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.setErrFn != nil {
		if err := s.setErrFn(key); err != nil {
			return err
		}
	}
	s.store[key] = value
	return nil
}

// Delete satisfies valkey.Client. The cache flow does not call Delete in
// MVP1 but the interface requires it.
func (s *Stub) Delete(_ context.Context, key string) error {
	s.deleteCnt.Add(1)
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.store, key)
	return nil
}

// Close is a no-op; the stub holds no external resources.
func (s *Stub) Close() error { return nil }

// Compile-time interface check — fails compilation if Stub drifts from the
// valkey.Client contract.
var _ valkey.Client = (*Stub)(nil)
