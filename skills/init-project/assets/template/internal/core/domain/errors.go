// Package domain holds the service's coded errors. A freshly scaffolded service has
// only the dependency codes its skeleton adapters raise; each domain added later
// brings its own codes (see .kiro/steering/errors.md).
package domain

import (
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/stderr"
)

// Service error codes (Appendix-E). Response code and message live in errorcatalog/errors.json;
// stdresp.ErrorHandler resolves them from the catalog and derives the HTTP status from the response
// code. The reserved codes NZQ-1001, NZQ-1002 and NZQ-9001 are common-lib's
// (stderr.MandatoryFieldMissing, stderr.InvalidFieldFormat, stderr.UnexpectedError).
var (
	ErrDatabaseUnavailable = stderr.Ref("NZQ-8001")
)

// NewDatabaseUnavailableError reports a failure of the Postgres datastore this service depends on
// → NZQ-8001 / 503. The driver error is carried as the cause: logged, never rendered.
func NewDatabaseUnavailableError(err error) error {
	return stderr.New(ErrDatabaseUnavailable, err)
}

// ErrorRefs lists every service code the domain raises for catalog validation.
func ErrorRefs() []stderr.Code {
	return []stderr.Code{ErrDatabaseUnavailable}
}
