from fastapi import Request
from slowapi import Limiter


def _client_ip(request: Request) -> str:
    # Prefer X-Forwarded-For set by the nginx gateway so the real browser IP
    # is used for rate limiting, not the gateway container's internal IP.
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_client_ip)
