# Account Service API Documentation

**Version:** 1.0
**Base URL:** `/`

## Overview

Account Service provides APIs for managing bank accounts.

## Endpoints

### Account

| Method | Path | Endpoint | File |
| ------ | ---- | -------- | ---- |
| `POST` | `/accounts` | Create | [create](account/create.yaml) |

## Common Error Responses

| Status | Code | Error Message | Description |
| ------ | ---- | ------------- | ----------- |
| 400 | `VALIDATION_ERROR` | ... | Request body failed validation (missing required field, type mismatch, or constraint violation) |
