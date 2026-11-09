package fix

type CreateAccountRequest struct {
	CustomerID  string `json:"customerId" binding:"required"`
	AccountType string `json:"accountType" binding:"required"`
	Items       []Item `json:"items,omitempty"`
}

type Item struct {
	Code string `json:"code" binding:"required"`
}

type AccountResponse struct {
	AccountID string `json:"accountId"`
}
