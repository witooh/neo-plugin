package valkey

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/alicebob/miniredis/v2"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// newTestClient returns a Client wired to an in-process miniredis instance.
// The mr instance is returned so tests can manipulate state (FastForward
// to expire TTLs, peek at stored keys to assert namespacing).
//
// The default prefix is a neutral "ns:" so tests can assert on the namespaced
// wire shape miniredis stores.
func newTestClient(t *testing.T) (Client, *miniredis.Miniredis) {
	t.Helper()
	mr := miniredis.RunT(t)
	c := NewClient(Config{Addr: mr.Addr(), KeyPrefix: "ns:"})
	t.Cleanup(func() { _ = c.Close() })
	return c, mr
}

// TestClient_SetThenGet covers the happy path: a value written with Set
// is returned verbatim by Get on the same key.
func TestClient_SetThenGet(t *testing.T) {
	t.Parallel()
	c, _ := newTestClient(t)

	require.NoError(t, c.Set(context.Background(), "foo", []byte("bar"), time.Minute))
	got, err := c.Get(context.Background(), "foo")
	require.NoError(t, err)
	assert.Equal(t, []byte("bar"), got)
}

// TestClient_GetMissReturnsErrNotFound proves that a Get on a missing key
// returns ErrNotFound — callers rely on this to distinguish cache miss
// from transport failure.
func TestClient_GetMissReturnsErrNotFound(t *testing.T) {
	t.Parallel()
	c, _ := newTestClient(t)

	_, err := c.Get(context.Background(), "nope")
	assert.True(t, errors.Is(err, ErrNotFound), "expected ErrNotFound, got %v", err)
}

// TestClient_TTLExpires verifies the TTL passed to Set is honoured by the
// underlying store. miniredis advances time only on FastForward, so the
// test is deterministic.
func TestClient_TTLExpires(t *testing.T) {
	t.Parallel()
	c, mr := newTestClient(t)

	require.NoError(t, c.Set(context.Background(), "tmp", []byte("v"), time.Second))
	mr.FastForward(2 * time.Second)

	_, err := c.Get(context.Background(), "tmp")
	assert.True(t, errors.Is(err, ErrNotFound))
}

// TestClient_Delete covers the third method: Delete removes the entry and
// subsequent Get returns ErrNotFound.
func TestClient_Delete(t *testing.T) {
	t.Parallel()
	c, _ := newTestClient(t)

	require.NoError(t, c.Set(context.Background(), "k", []byte("v"), time.Minute))
	require.NoError(t, c.Delete(context.Background(), "k"))

	_, err := c.Get(context.Background(), "k")
	assert.True(t, errors.Is(err, ErrNotFound))
}

func TestClient_KeyPrefixApplied(t *testing.T) {
	t.Parallel()
	c, mr := newTestClient(t)

	require.NoError(t, c.Set(context.Background(), "abc", []byte("x"), time.Minute))

	got, err := mr.Get("ns:abc")
	require.NoError(t, err)
	assert.Equal(t, "x", got)

	// And the un-prefixed key must not exist — proving the prefix is the
	// only address.
	_, err = mr.Get("abc")
	assert.Error(t, err)
}

func TestClient_PrefixIsolated(t *testing.T) {
	t.Parallel()
	mr := miniredis.RunT(t)

	clientA := NewClient(Config{Addr: mr.Addr(), KeyPrefix: "a:"})
	clientB := NewClient(Config{Addr: mr.Addr(), KeyPrefix: "b:"})
	t.Cleanup(func() {
		_ = clientA.Close()
		_ = clientB.Close()
	})

	const sharedKey = "00000000-0000-0000-0000-000000000001"

	require.NoError(t, clientA.Set(context.Background(), sharedKey, []byte("from-a"), time.Minute))
	require.NoError(t, clientB.Set(context.Background(), sharedKey, []byte("from-b"), time.Minute))

	gotA, err := clientA.Get(context.Background(), sharedKey)
	require.NoError(t, err)
	assert.Equal(t, []byte("from-a"), gotA, "client A must read its own namespace")

	gotB, err := clientB.Get(context.Background(), sharedKey)
	require.NoError(t, err)
	assert.Equal(t, []byte("from-b"), gotB, "client B must read its own namespace; no cross-prefix collision")

	// Direct miniredis inspection: each prefix occupies a distinct slot.
	rawA, err := mr.Get("a:" + sharedKey)
	require.NoError(t, err)
	assert.Equal(t, "from-a", rawA)
	rawB, err := mr.Get("b:" + sharedKey)
	require.NoError(t, err)
	assert.Equal(t, "from-b", rawB)
}

// TestNewClient_PanicsOnEmptyKeyPrefix asserts the wiring guard: an empty
// KeyPrefix is a developer error (every cache user must declare its namespace)
// and surfaces at startup rather than as silent collisions at runtime.
func TestNewClient_PanicsOnEmptyKeyPrefix(t *testing.T) {
	t.Parallel()
	mr := miniredis.RunT(t)
	assert.Panics(t, func() {
		_ = NewClient(Config{Addr: mr.Addr()}) // KeyPrefix unset — must panic
	})
}
