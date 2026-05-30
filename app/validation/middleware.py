from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import ALLOWED_HOSTS

# =========================
# Rate Limiter
# =========================
limiter = Limiter(key_func=get_remote_address)


# =========================
# Exception Handlers
# =========================
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
    )


def register_middleware(app: FastAPI) -> None:
    """Attach all middleware and exception handlers to the app."""
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[f"http://{host}" for host in ALLOWED_HOSTS]
        + [f"https://{host}" for host in ALLOWED_HOSTS],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
