from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.user import UserRole


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """Payload for POST /api/auth/register."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    """Payload for POST /api/auth/login."""

    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    """Public user representation — never exposes hashed_password."""

    id: str
    email: EmailStr
    username: str
    role: str        # stored as string in DB; frontend reads it directly
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TokenData(BaseModel):
    """Claims extracted from a decoded JWT."""

    user_id: str | None = None
