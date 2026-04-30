from dotenv import load_dotenv
from email.message import EmailMessage
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from html import escape
from jinja2 import Template
from pathlib import Path
from pydantic import BaseModel, EmailStr, Field, field_validator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from urllib.parse import urlparse
import smtplib
import os
import logging

# =========================
# Load environment variables
# =========================
load_dotenv()

# =========================
# Logging
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# Rate Limiter
# =========================
limiter = Limiter(key_func=get_remote_address)

# =========================
# Environment Config
# =========================
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "ALLOWED_HOSTS", "localhost:3000,localhost:8000, 127.0.0.1:3000, 127.0.0.1:8000"
    ).split(",")
]

RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# SMTP Config
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_EMAIL = os.getenv("SMTP_EMAIL", SMTP_USER)

# =========================
# Validate Config
# =========================
if not all(
    [
        SMTP_HOST,
        SMTP_PORT,
        SMTP_USER,
        SMTP_PASSWORD,
        RECIPIENT_EMAIL,
        ALLOWED_HOSTS,
        SMTP_EMAIL,
    ]
):
    raise ValueError("SMTP configuration missing")

# =========================
# FastAPI App
# =========================
app = FastAPI(
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{host}" for host in ALLOWED_HOSTS],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


# =========================
# Exception Handlers
# =========================
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"},
    )


# =========================
# Request Schema
# =========================
class Form(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    message: str = Field(..., min_length=1, max_length=5000)

    @field_validator("name", "message")
    @classmethod
    def strip_fields(cls, v: str):
        return v.strip()


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


# =========================
# SMTP Email Sender
# =========================
def send_email(name: str, email: str, message: str) -> dict:
    try:
        msg = EmailMessage()
        safe_name = escape(name)
        safe_email = escape(email)
        safe_message = escape(message).replace("\n", "<br>")
        template_path = Path(__file__).parent / "templates" / "email_template.html"
        template = Template(template_path.read_text(encoding="utf-8"))

        safe_subject_name = name.replace("\n", "").replace("\r", "")
        msg["Subject"] = f"New Form Submission from {safe_subject_name}"
        msg["From"] = SMTP_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        msg["Reply-To"] = email

        msg.set_content(
            f"New form submission from {name}\n\nName: {name}\nEmail: {email}\n\nMessage:\n{message}"
        )

        msg.add_alternative(
            template.render(
                name=safe_name,
                email=safe_email,
                message=safe_message,
            ),
            subtype="html",
        )

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully from {email}")
        return {"message": "Email sent successfully", "status": "success"}

    except Exception as e:
        logger.error(f"SMTP email failed: {str(e)}")
        raise


# =========================
# API Endpoint
# =========================
@app.post("/submit-form")
@limiter.limit("5/minute")
async def submit_form(form: Form, request: Request):
    if not is_allowed_origin(request):
        logger.warning(f"Blocked request from {request.client.host}")
        raise HTTPException(status_code=403, detail="Origin not allowed")

    try:
        result = send_email(form.name, form.email, form.message)
        logger.info(f"Form submitted by {form.email}")
        return result
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send email")
