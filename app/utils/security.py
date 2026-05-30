from fastapi import Request
from urllib.parse import urlparse
from app.config import ALLOWED_HOSTS


# =========================
# Security: Origin Check
# =========================
def is_allowed_origin(request: Request) -> bool:
    origin = request.headers.get("origin") or request.headers.get("referer")

    if not origin:
        return False

    try:
        parsed = urlparse(origin)
        return parsed.netloc in ALLOWED_HOSTS
    except Exception:
        return False
