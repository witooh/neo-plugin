package errorcatalog_test

import (
	"encoding/json"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"example.com/neo/service/internal/core/domain"
	"example.com/neo/service/internal/core/domain/errorcatalog"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/stderr"
)

// The embedded catalog passes common-lib validation, carries the service prefix, and declares every
// code the domain raises (a missing one would render as NZQ-9001 at runtime).
func TestCatalogLoadsAndCoversEveryDomainCode(t *testing.T) {
	catalog, err := stderr.LoadCatalog(errorcatalog.JSON())

	require.NoError(t, err)
	assert.Equal(t, "NZQ", catalog.Prefix())
	require.NoError(t, catalog.Require(domain.ErrorRefs()...))
}

// errors.json holds exactly the service rows, one per code in domain.ErrorRefs; an extra row would be
// a code nobody raises.
func TestCatalogFileHasNoUnraisedCodes(t *testing.T) {
	var file struct {
		Prefix string `json:"prefix"`
		Errors []struct {
			Code string `json:"code"`
		} `json:"errors"`
	}
	require.NoError(t, json.Unmarshal(errorcatalog.JSON(), &file))

	got := make([]string, 0, len(file.Errors))
	for _, e := range file.Errors {
		got = append(got, e.Code)
	}
	refs := domain.ErrorRefs()
	want := make([]string, 0, len(refs))
	for _, c := range refs {
		want = append(want, c.ID())
	}
	assert.ElementsMatch(t, want, got)
}

func TestJSONReturnsACopy(t *testing.T) {
	first := errorcatalog.JSON()
	first[0] = 'x'

	assert.Equal(t, byte('{'), errorcatalog.JSON()[0])
}
