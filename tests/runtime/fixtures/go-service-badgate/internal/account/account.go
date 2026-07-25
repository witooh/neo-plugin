package account

import "errors"

// ErrNotFound is returned by Repository.Find when no account matches the id.
var ErrNotFound = errors.New("account not found")

type Account struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	Balance int64  `json:"balance"`
}
