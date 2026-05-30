import logging
from fastapi import FastAPI

from app.config import DEBUG
from app.middleware import register_middleware
from app.routers import form

# =========================
# Logging
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# FastAPI App
# =========================
app = FastAPI(
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
)

register_middleware(app)

app.include_router(form.router)
