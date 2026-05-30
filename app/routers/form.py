from fastapi import APIRouter, HTTPException, Request
import logging

from app.schemas.form import Form
from app.services.email import handle_email_sending
from app.utils.security import is_allowed_origin
from app.middleware import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


# =========================
# API Endpoint
# =========================
@router.post("/submit-form")
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
