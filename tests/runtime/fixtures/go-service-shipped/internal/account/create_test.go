package account

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func postAccounts(t *testing.T, body string) *httptest.ResponseRecorder {
	t.Helper()
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/accounts", strings.NewReader(body))
	newTestHandler().CreateAccount(rec, req)
	return rec
}

// AC-001 — a valid body returns 201 and the created account with a UUID v4 id.
func TestCreateAccount_Created(t *testing.T) {
	rec := postAccounts(t, `{"name":"Savings","balance":100}`)

	if rec.Code != http.StatusCreated {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusCreated)
	}

	var got Account
	if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if got.Name != "Savings" || got.Balance != 100 {
		t.Errorf("got %+v, want name=Savings balance=100", got)
	}
	if len(got.ID) != 36 {
		t.Errorf("id = %q, want a 36-char UUID", got.ID)
	}
}

// AC-002 — a name longer than 100 characters returns 400.
func TestCreateAccount_NameTooLong(t *testing.T) {
	rec := postAccounts(t, `{"name":"`+strings.Repeat("a", 101)+`","balance":100}`)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}

// AC-003 — a negative balance returns 400.
func TestCreateAccount_NegativeBalance(t *testing.T) {
	rec := postAccounts(t, `{"name":"Savings","balance":-1}`)

	if rec.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusBadRequest)
	}
}
