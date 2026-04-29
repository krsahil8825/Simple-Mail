from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
from slowapi.util import get_remote_address
from urllib.parse import urlparse
import os
import resend
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)

# Load config from environment
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost:3000,localhost:8000").split(",")
]
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "contact@krsahil.co.in")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")

# Validate required config
if not RESEND_API_KEY:
    raise ValueError("RESEND_API_KEY not configured")

resend.api_key = RESEND_API_KEY

app = FastAPI(
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Too many requests"})


class Form(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    message: str = Field(..., min_length=1, max_length=5000)

    @field_validator("name", "message")
    @classmethod
    def strip_fields(cls, v: str):
        return v.strip()


def is_allowed_origin(request: Request) -> bool:
    """Check if request is from allowed host"""
    origin = request.headers.get("origin") or request.headers.get("referer")

    if not origin:
        return False

    try:
        parsed = urlparse(origin)
        return parsed.netloc in ALLOWED_HOSTS
    except Exception:
        return False


def send_email(name: str, email: str, message: str) -> dict:
    """Send form submission email"""
    try:
        response = resend.Emails.send(
            {
                "from": SENDER_EMAIL,
                "to": RECIPIENT_EMAIL,
                "subject": f"New Form Submission from {name}",
                "reply_to": email,
                "html": f"""
                <h3>New Form Submission</h3>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Message:</strong><br>{message}</p>
            """,
            }
        )
        logger.info(f"Email sent successfully: {response['id']}")
        return {"message": "Email sent successfully", "status": "success"}
    except Exception as e:
        logger.error(f"Email sending failed: {str(e)}")
        raise


@app.post("/submit-form")
@limiter.limit("5/minute")
async def submit_form(form: Form, request: Request):
    """Submit a form with validation and email notification"""
    if not is_allowed_origin(request):
        logger.warning(f"Blocked request from {request.client.host}")
        raise HTTPException(status_code=403, detail="Origin not allowed")

    try:
        result = send_email(form.name, form.email, form.message)
        logger.info(f"Form submitted from {form.email}")
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send email")
