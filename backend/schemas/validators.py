"""Common input validators and sanitizers for critical fields."""
import re
import html

TICKER_RE = re.compile(r'^[A-Z0-9_\-]{1,20}$')


def validate_ticker(symbol: str) -> str:
    if not TICKER_RE.match(symbol or ''):
        raise ValueError('Invalid ticker format')
    return symbol


def validate_quantity(qty: float) -> float:
    if qty is None or qty <= 0:
        raise ValueError('Quantity must be positive')
    if qty > 1e9:
        raise ValueError('Quantity too large')
    return qty


def sanitize_text(value: str, max_len: int = 2000) -> str:
    if value is None:
        return ''
    v = str(value)[:max_len]
    return html.escape(v, quote=True)


