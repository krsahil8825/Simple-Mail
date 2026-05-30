from pydantic import BaseModel, EmailStr, Field, field_validator


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

class ContactForm(Form):
    purpose: str = Field(..., min_length=1, max_length=200)