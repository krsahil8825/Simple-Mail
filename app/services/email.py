from email.message import EmailMessage
from html import escape
from jinja2 import Template
from typing import Optional, Dict
from pathlib import Path
import smtplib
import logging

from app.config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_EMAIL,
    RECIPIENT_EMAIL,
)

logger = logging.getLogger(__name__)


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

        # Basic header sanitization to prevent header injection
        def _sanitize_header(v: str) -> str:
            return v.replace("\r", "").replace("\n", "").strip()

        msg["From"] = SMTP_EMAIL
        msg["Subject"] = _sanitize_header(subject)
        msg["To"] = _sanitize_header(to_email)
        if reply_to:
            msg["Reply-To"] = _sanitize_header(reply_to)

        msg.set_content(plain_text)

        if template_name:
            template_path = Path(__file__).parent.parent / "templates" / template_name
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
    thank_you_text = "Thank you for your message. I will contact you within 1 or 2 business days. Have a great day!"

    send_email(
        subject=thank_you_subject,
        to_email=email,
        plain_text=thank_you_text,
        template_name="thank_you_template.html",
        template_ctx={"name": name, "message": thank_you_text},
    )
