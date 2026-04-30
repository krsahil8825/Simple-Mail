from dotenv import load_dotenv
from email.message import EmailMessage
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from html import escape
from jinja2 import Template
from typing import Optional, Dict
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
    allow_origins=[f"http://{host}" for host in ALLOWED_HOSTS]
    + [f"https://{host}" for host in ALLOWED_HOSTS],
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
def send_email(
    subject: str,
    to_email: str,
    plain_text: str,
    template_name: Optional[str] = None,
    template_ctx: Optional[Dict] = None,
    reply_to: Optional[str] = None,
) -> dict:
    """Send an email using SMTP. If `template_name` is provided, render HTML alternative.

    Returns a dict with message and status on success, raises on failure.
    """
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = SMTP_EMAIL
        msg["To"] = to_email
        if reply_to:
            msg["Reply-To"] = reply_to

        msg.set_content(plain_text)

        if template_name:
            template_path = Path(__file__).parent / "templates" / template_name
            template = Template(template_path.read_text(encoding="utf-8"))
            ctx = template_ctx or {}

            # Escape all context values to prevent XSS injection
            safe_ctx = {k: escape(str(v)) for k, v in ctx.items()}

            html_body = template.render(**safe_ctx)
            msg.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent successfully to {to_email}")
        return {"message": "Email sent successfully", "status": "success"}

    except Exception as e:
        logger.error(f"SMTP email failed: {str(e)}")
        raise


def handle_email_sending(name: str, email: str, message: str) -> None:
    """Handle sending the internal notification and a thank-you email to the submitter."""

    # Send internal notification to site owner
    safe_subject_name = name.replace("\n", "").replace("\r", "")
    notification_subject = f"New Form Submission from {safe_subject_name}"
    notification_plain = f"New form submission from {name}\n\nName: {name}\nEmail: {email}\n\nMessage:\n{message}"

    send_email(
        subject=notification_subject,
        to_email=RECIPIENT_EMAIL,
        plain_text=notification_plain,
        template_name="email_template.html",
        template_ctx={
            "name": name,
            "email": email,
            "message": message.replace("\n", "<br>"),
        },
        reply_to=email,
    )

    # Send thank-you email to the submitter
    thank_you_subject = "Thank you for your message"
    thank_you_text = (
        "Thank you for your message. I will contact you within 1 or 2 business days. Have a great day!"
    )

    send_email(
        subject=thank_you_subject,
        to_email=email,
        plain_text=thank_you_text,
        template_name="thank_you_template.html",
        template_ctx={"name": name, "message_text": thank_you_text},
    )


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
        # Use the handler to send both notification and thank-you emails
        handle_email_sending(form.name, form.email, form.message)
        logger.info(f"Form submitted by {form.email}")
        return {"message": "Form submitted and emails sent", "status": "success"}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send email")
