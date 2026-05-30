from dotenv import load_dotenv
import os

# =========================
# Load environment variables
# =========================
load_dotenv()

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
