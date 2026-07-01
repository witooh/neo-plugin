package postgres

import (
	"database/sql"
	"encoding/json"
	"time"

	"github.com/shopspring/decimal"
	"github.com/sqlc-dev/pqtype"
)

func NullStringToStr(v sql.NullString) string {
	if v.Valid {
		return v.String
	}
	return ""
}

func NullBoolToBool(v sql.NullBool) bool {
	if v.Valid {
		return v.Bool
	}
	return false
}

func StrToNullString(s string) sql.NullString {
	if s == "" {
		return sql.NullString{Valid: false}
	}
	return sql.NullString{Valid: true, String: s}
}

func BoolToNullBool(b bool) sql.NullBool {
	return sql.NullBool{Valid: true, Bool: b}
}

func NullTimeToTimePtr(v sql.NullTime) *time.Time {
	if !v.Valid {
		return nil
	}
	t := v.Time
	return &t
}

func TimePtrToNullTime(t *time.Time) sql.NullTime {
	if t == nil {
		return sql.NullTime{Valid: false}
	}
	return sql.NullTime{Time: *t, Valid: true}
}

func NullDecimalToFloat64(v decimal.NullDecimal) float64 {
	if !v.Valid {
		return 0
	}
	f, _ := v.Decimal.Float64()
	return f
}

func NullRawMessageToBytes(v pqtype.NullRawMessage) json.RawMessage {
	if !v.Valid {
		return nil
	}
	return json.RawMessage(v.RawMessage)
}

func BytesToNullRawMessage(b json.RawMessage) pqtype.NullRawMessage {
	if b == nil {
		return pqtype.NullRawMessage{Valid: false}
	}
	return pqtype.NullRawMessage{RawMessage: b, Valid: true}
}
