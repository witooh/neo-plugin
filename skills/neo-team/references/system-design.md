# System Design — [Feature/Module Name]

**Version:** [version]
**Created Date:** [date]
**Created By:** Architect
**AC Document:** [path to acceptance criteria document, e.g., docs/acceptance-criteria.md]

---

## Overview

[1-2 sentences: what this design covers and why]

---

## API Contracts

### [Endpoint Name] — [short description]

| Field | Value |
|-------|-------|
| Method | [GET/POST/PUT/DELETE/PATCH] |
| Path | [/api/v1/...] |
| Auth | [auth pattern] |
| Covers AC | [AC-001, AC-002, ...] |

**Request Body:**

```json
{
  "field": "type — validation rule (from AC business rule)"
}
```

**Response 200/201:**

```json
{
  "field": "type"
}
```

**Error Responses:**

| Status | Error Code | Message | Covers AC |
|--------|------------|---------|-----------|
| 400 | INVALID_INPUT | [specific message] | AC-XXX |
| 404 | NOT_FOUND | [specific message] | AC-XXX |
| 409 | CONFLICT | [specific message] | AC-XXX |

---

## Module Design

### Entity: [EntityName]

| Field | Type | Description | Business Rule |
|-------|------|-------------|---------------|
| [field] | [type] | [description] | [from AC] |

### Domain Service: [ServiceName]

Cross-entity business logic — calculations, validations, or coordination between entities. Not flow orchestration (that belongs to Usecase).

| Method | Signature | Description | Covers AC |
|--------|-----------|-------------|-----------|
| [method] | [input → output] | [business logic it performs] | AC-XXX |

### Repository: [RepositoryName]

| Method | Signature | Description |
|--------|-----------|-------------|
| [method] | [input → output] | [what it does] |

### Usecase: [UsecaseName]

Business flow orchestration — calls domain services and repositories in sequence. Usecase owns the flow, not the logic.

| Method | Signature | Description | Covers AC |
|--------|-----------|-------------|-----------|
| [method] | [input → output] | [what it does] | AC-XXX |

### File Structure

```
[module]/
├── entity.go (or .ts, .py, etc.)
├── repository.go
├── usecase.go
└── handler.go
```

---

## ADR (if applicable)

### ADR-001: [Decision Title]

**Context:** [why this decision is needed]

**Options Considered:**
1. [option 1] — [pros/cons]
2. [option 2] — [pros/cons]

**Decision:** [what was chosen and why]

**Consequences:** [trade-offs accepted]

---

## AC Traceability

| AC-ID | Design Element | Type |
|-------|----------------|------|
| AC-001 | [endpoint / entity field / usecase method / error response] | [API / Module / Validation / Error] |
| AC-002 | [design element] | [type] |

**Coverage:** [X/Y AC-IDs covered — if any AC is not covered, explain why as Open Question]

---

## Security Flags

- [anything that Security specialist should review — e.g., new auth flow, sensitive data handling, external API calls]

---

## Open Questions

- [anything unclear or technically infeasible from AC — needs user or BA clarification]
