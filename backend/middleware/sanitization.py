"""Request payload sanitization middleware.

Features:
- Escape HTML in string fields
- Enforce max length for strings
- Validate basic scalar types; reject overly deep/nested payloads
- Restrict allowed content types to application/json for mutation endpoints
"""
import json
import html
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse


MAX_STRING_LEN = 2000
MAX_DEPTH = 5
MAX_LIST_LEN = 1000


def _sanitize_value(value: Any, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        raise ValueError("Payload too deep")
    if isinstance(value, str):
        # Trim and escape HTML
        v = value[:MAX_STRING_LEN]
        return html.escape(v, quote=True)
    if isinstance(value, list):
        if len(value) > MAX_LIST_LEN:
            raise ValueError("List too long")
        return [_sanitize_value(v, depth + 1) for v in value]
    if isinstance(value, dict):
        return {k: _sanitize_value(v, depth + 1) for k, v in value.items()}
    # Scalars pass-through
    return value


class SanitizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # Only sanitize JSON request bodies
            if request.method in ("POST", "PUT", "PATCH"):
                content_type = request.headers.get("content-type", "")
                if "application/json" not in content_type:
                    return JSONResponse({"detail": "Unsupported content-type"}, status_code=415)
                body_bytes = await request.body()
                if body_bytes:
                    try:
                        data = json.loads(body_bytes.decode("utf-8"))
                    except Exception:
                        return JSONResponse({"detail": "Invalid JSON"}, status_code=400)
                    try:
                        sanitized = _sanitize_value(data)
                    except ValueError as ve:
                        return JSONResponse({"detail": str(ve)}, status_code=400)
                    # Replace request stream with sanitized JSON
                    request._body = json.dumps(sanitized).encode("utf-8")
        except Exception:
            return JSONResponse({"detail": "Sanitization error"}, status_code=400)
        return await call_next(request)


