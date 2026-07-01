// Package clock provides an injectable wall-clock abstraction so that
// time-dependent logic can be exercised deterministically in tests. Production
// code wires System(); tests wire a fixed clock (see clocktest.Stub).
package clock

import "time"

// Clock reports the current time. Inject it wherever business logic would
// otherwise call time.Now() directly, so the "current time" can be fixed in tests.
type Clock interface {
	Now() time.Time
}

// systemClock is the production Clock; it reads the real wall clock.
type systemClock struct{}

func (systemClock) Now() time.Time { return time.Now() }

// System returns the production Clock backed by time.Now().
func System() Clock { return systemClock{} }
