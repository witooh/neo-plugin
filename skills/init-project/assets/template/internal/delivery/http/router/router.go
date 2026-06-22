// Package router wires the gin engine: the standard middleware chain and the
// health probe. It is the HTTP-composition sub-layer — analogous to cmd/api but
// scoped to routing — and the one inbound package permitted to import the handler
// packages. Each resource's route registration lives in its own file (neo adds
// account.go, balance.go, … as it builds handlers) so that adding or changing one
// resource's routes touches a single file.
package router

import (
	"net/http"

	"github.com/gin-gonic/gin"

	"example.com/neo/service/internal/delivery/http/middleware"
)

// Handlers bundles every HTTP handler the router wires. A freshly scaffolded
// service has none; the composition root (cmd/api) builds the concrete handlers
// and neo adds a field here per resource (e.g. Account *account.Handler).
type Handlers struct{}

// New builds the gin engine with the standard middleware chain and the health
// probe. neo registers resource route groups here as handlers are added — e.g.
// `accounts := r.Group("/accounts"); registerAccount(accounts, h.Account)`.
func New(h Handlers, serviceID string) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	gin.EnableJsonDecoderDisallowUnknownFields()
	r := gin.New()

	middleware.Setup(r, serviceID)

	r.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok"})
	})

	return r
}
