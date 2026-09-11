package middleware_test

import (
	"bytes"
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"{{MODULE_PATH}}/internal/core/domain/audit"
	"{{MODULE_PATH}}/internal/delivery/http/middleware"
)

// stubAuditWriter captures Insert calls. account-service MR 196 covered the
// middleware only via e2e; payment-gateway had httptest. This stub is the
// portable coverage so the middleware package stays testable without DB.
type stubAuditWriter struct {
	records []*audit.AuditLog
	err     error
}

func (s *stubAuditWriter) Insert(_ context.Context, log *audit.AuditLog) error {
	if s.err != nil {
		return s.err
	}
	s.records = append(s.records, log)
	return nil
}

func buildTestEngine(writer audit.AuditLogRepository, path string, statusCode int, responseBody string) *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.Use(middleware.Audit(writer))
	r.POST(path, func(c *gin.Context) {
		if responseBody != "" {
			c.Data(statusCode, "application/json", []byte(responseBody))
			return
		}
		c.Status(statusCode)
	})
	return r
}

func performRequest(r *gin.Engine, path, body string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(http.MethodPost, path, bytes.NewBufferString(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
	return w
}

func TestAudit_successResponse(t *testing.T) {
	writer := &stubAuditWriter{}
	r := buildTestEngine(writer, "/v1/probe", http.StatusOK, `{"responseCode":"0000"}`)
	reqBody := `{"id":"1"}`

	performRequest(r, "/v1/probe", reqBody)

	require.Len(t, writer.records, 1)
	rec := writer.records[0]
	assert.Equal(t, audit.AuditStatus_SUCCESS, rec.Status())
	assert.Equal(t, int16(http.StatusOK), rec.HttpStatus())
	assert.Equal(t, "POST", rec.HttpMethod())
	assert.Equal(t, "/v1/probe", rec.Route())
	assert.Equal(t, "0000", rec.ResponseCode())
	assert.Equal(t, reqBody, rec.RawRequest())
	assert.Contains(t, rec.RawResponse(), `"responseCode":"0000"`)
	assert.GreaterOrEqual(t, rec.DurationMs(), int64(0))
}

func TestAudit_failedResponse(t *testing.T) {
	writer := &stubAuditWriter{}
	r := buildTestEngine(writer, "/v1/probe", http.StatusBadRequest, `{"responseCode":"002","message":"invalid request"}`)

	performRequest(r, "/v1/probe", `{}`)

	require.Len(t, writer.records, 1)
	rec := writer.records[0]
	assert.Equal(t, audit.AuditStatus_FAILED, rec.Status())
	assert.Equal(t, int16(http.StatusBadRequest), rec.HttpStatus())
	assert.Equal(t, "002", rec.ResponseCode())
	assert.Equal(t, "invalid request", rec.FailureReason())
}

func TestAudit_retryProducesSeparateRows(t *testing.T) {
	writer := &stubAuditWriter{}
	r := buildTestEngine(writer, "/v1/probe", http.StatusOK, `{"responseCode":"0000"}`)

	performRequest(r, "/v1/probe", `{}`)
	performRequest(r, "/v1/probe", `{}`)

	require.Len(t, writer.records, 2)
	assert.NotEqual(t, writer.records[0].RequestId(), writer.records[1].RequestId())
}

func TestAudit_writerFailureContinues(t *testing.T) {
	writer := &stubAuditWriter{err: assert.AnError}
	r := buildTestEngine(writer, "/v1/probe", http.StatusOK, `{"responseCode":"0000"}`)

	w := performRequest(r, "/v1/probe", `{}`)

	assert.Equal(t, http.StatusOK, w.Code)
}

func TestAudit_nilWriterNoPanic(t *testing.T) {
	r := buildTestEngine(nil, "/v1/probe", http.StatusOK, `{"status":"ok"}`)

	assert.NotPanics(t, func() {
		w := performRequest(r, "/v1/probe", `{}`)
		assert.Equal(t, http.StatusOK, w.Code)
	})
}
