package account

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

func newTestHandler() *Handler {
	return NewHandler(NewInMemoryRepository(map[string]*Account{
		"acc-1": {ID: "acc-1", Name: "Alice", Balance: 1000},
	}))
}

func TestGetAccount_Found(t *testing.T) {
	rec := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/accounts/acc-1", nil)

	newTestHandler().GetAccount(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d", rec.Code, http.StatusOK)
	}

	var got Account
	if err := json.NewDecoder(rec.Body).Decode(&got); err != nil {
		t.Fatalf("decode body: %v", err)
	}
	if got.ID != "acc-1" {
		t.Errorf("id = %q, want %q", got.ID, "acc-1")
	}
}
