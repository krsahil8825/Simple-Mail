from fastapi import APIRouter, HTTPException, Request
import logging
from app.config import RATE_LIMIT, DEBUG
from app.schemas.form import Form, ContactForm
from app.services.email import handle_email_sending
from app.utils.security import is_allowed_origin
from app.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# =========================
# API Endpoint
# =========================
@router.post("/submit-form")
@limiter.limit(RATE_LIMIT)
async def submit_form(form: Form, request: Request):
    if not DEBUG and not is_allowed_origin(request):
        logger.warning(f"Blocked request from {request.client.host}")
        raise HTTPException(status_code=403, detail="Origin not allowed")

    try:
        # Use the handler to send both notification and thank-you emails
        handle_email_sending(form.name, form.email, form.message)
        logger.info(f"Form submitted by {form.email}")
        return {"message": "Form submitted and emails sent", "status": "success"}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send email")


@router.post("/contact")
@limiter.limit(RATE_LIMIT)
async def contact_form(form: ContactForm, request: Request):
    if not DEBUG and not is_allowed_origin(request):
        logger.warning(f"Blocked request from {request.client.host}")
        raise HTTPException(status_code=403, detail="Origin not allowed")

    try:
        # Use the handler to send both notification and thank-you emails
        handle_email_sending(
            form.name,
            form.email,
            f"Purpose: {form.purpose}\n\nMessage:\n{form.message}",
        )
        logger.info(
            f"Contact form submitted by {form.email} with purpose: {form.purpose}"
        )
        return {
            "message": "Contact form submitted and emails sent",
            "status": "success",
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to send email")
