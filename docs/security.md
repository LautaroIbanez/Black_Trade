# Input Sanitization & Validation

## Middleware
- SanitizationMiddleware (backend/middleware/sanitization.py):
  - Escapes HTML entities in all JSON string fields
  - Enforces max string length (2,000 chars)
  - Rejects overly deep payloads (> 5 levels) and huge lists (> 1,000)
  - Requires Content-Type: application/json for POST/PUT/PATCH; returns 415 otherwise

## Validators (backend/schemas/validators.py)
- validate_ticker: restricts to [A-Z0-9_\-]{1,20}
- validate_quantity: positive numeric, capped to prevent abuse
- sanitize_text: safe HTML-escaped text with length limit

## Applied Endpoints
- Recommendations feedback sanitizes notes and checklist string fields before persistence.
- Global middleware sanitizes all JSON payloads prior to route handling.

## Developer Guidance
- Always define Pydantic models with explicit types and field validators.
- Avoid storing raw user HTML; if needed, use a strict whitelist renderer.
- Validate tickers and numeric ranges server-side; never trust client inputs.

## Testing
- tests/security/test_input_sanitization.py covers XSS payloads and invalid content-type.


