# Central rate limiter instance.
# Import `limiter` anywhere you need to apply limits.
# Import `rate_limit_exceeded_handler` and register it in main.py.
#
# Limits are per IP address.
# In production behind a reverse proxy (nginx, Cloudflare),
# set REAL_IP_HEADER in your config so the real client IP is used
# rather than the proxy IP.

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse


# Single shared limiter instance used across all routers
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    headers_enabled=True,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Called when any rate limit is exceeded.
    Returns the same envelope shape as the rest of the API.
    """
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "status":  429,
            "error":   f"Rate limit exceeded. Try again later.",
            "retry_after": exc.retry_after,
        },
        headers={
            "Retry-After":        str(exc.retry_after),
            "X-RateLimit-Limit":  str(exc.limit.limit),
        }
    )