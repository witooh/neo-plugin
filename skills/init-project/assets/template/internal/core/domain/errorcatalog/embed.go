// Package errorcatalog embeds the service's Appendix-E error catalog (errors.json), which
// stderr.LoadCatalog validates at startup. The human-readable table it mirrors is the
// Appendix-E section of README.md.
package errorcatalog

import (
	"bytes"
	_ "embed"
)

//go:embed errors.json
var errorsJSON []byte

// JSON returns a copy of the embedded catalog, so a caller cannot mutate the shared bytes.
func JSON() []byte {
	return bytes.Clone(errorsJSON)
}
