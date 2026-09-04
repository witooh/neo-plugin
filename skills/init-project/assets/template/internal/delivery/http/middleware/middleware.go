// Package middleware bundles the standard gin middleware chain for the HTTP
// delivery layer. It wraps the shared common-lib middleware — it does not
// reimplement it — so the service keeps correlation-id / request-id / HTTP
// logging / standard error rendering / panic recovery behaviour.
package middleware

import (
	"github.com/gin-gonic/gin"

	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/logger"
	commonmw "gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/middleware"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/stdresp"
)

// Setup applies the standard middleware chain (common-lib v2.2.4).
//
// Order: CorrelationId → RequestId → LoggingMiddleware → GinErrorHandler → Recovery.
// LoggingMiddleware and GinErrorHandler wrap Recovery so a recovered panic is
// still logged (one http.server.request.completed line) and still rendered as JSON.
func Setup(r *gin.Engine, serviceID string) {
	r.Use(commonmw.CorrelationIdMiddleware())
	r.Use(commonmw.RequestIdMiddleware())
	r.Use(commonmw.LoggingMiddleware(logger.GetLogger()))
	r.Use(stdresp.GinErrorHandler(serviceID))
	r.Use(commonmw.Recovery())
}
