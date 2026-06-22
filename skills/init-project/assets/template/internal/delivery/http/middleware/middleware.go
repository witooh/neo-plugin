// Package middleware bundles the standard gin middleware chain for the HTTP
// delivery layer. It wraps the shared common-lib middleware — it does not
// reimplement it — so the service keeps service-id / correlation-id / standard
// error rendering / error logging / panic recovery behaviour.
package middleware

import (
	"github.com/gin-gonic/gin"

	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/logger"
	commonmw "gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/middleware"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/stdresp"
)

// Setup applies the standard middleware chain (matches the previous
// cmd/api newRouter()).
func Setup(r *gin.Engine, serviceID string) {
	r.Use(commonmw.ServiceIdMiddleware(serviceID))
	r.Use(commonmw.CorrelationIdMiddleware())
	r.Use(stdresp.GinErrorHandler(serviceID))
	r.Use(commonmw.ErrorLoggingMiddleware(logger.GetLogger()))
	r.Use(commonmw.Recovery())
}
