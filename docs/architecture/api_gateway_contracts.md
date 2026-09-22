# API Gateway Contracts & Middleware Standards

Specification for API contracts, pagination headers, and cross-origin security standards.

## Response Standards

All collection endpoints (`/api/v1/sessions`, `/api/v1/alerts`, `/api/v1/slots`) follow standard array responses for client compatibility while transmitting total count metadata in standard HTTP headers:

```http
HTTP/1.1 200 OK
Content-Type: application/json
X-Total-Count: 124
Access-Control-Expose-Headers: X-Total-Count
```

## Standard Error Response Envelope

```json
{
  "detail": {
    "error_code": "RESOURCE_NOT_FOUND",
    "message": "Parking slot 'X-99' does not exist in the configured zone.",
    "timestamp": "2026-09-22T10:45:00Z"
  }
}
```

## Standard Status Codes
| HTTP Status | Meaning | Usage |
|---|---|---|
| `200 OK` | Success | Standard read/update response |
| `201 Created` | Created | New session, slot, or incident recorded |
| `400 Bad Request` | Validation Error | Malformed coordinates or invalid vehicle category |
| `401 Unauthorized` | Missing / Invalid Key | Missing `x-api-key` for edge telemetry ingestion |
| `409 Conflict` | Unique Constraint | Duplicate license plate or active track allocation conflict |
| `500 Server Error` | Unhandled Exception | Internal runtime failure with diagnostic tracking ID |
