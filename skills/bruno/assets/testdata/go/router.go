package fix

func Register(r Router, h *Handler) {
	r.POST("/v1/accounts", h.Create)
	r.GET("/v1/accounts/:accountId", h.Get)
}
