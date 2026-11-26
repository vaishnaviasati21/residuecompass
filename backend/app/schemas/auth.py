"""Auth request / response shapes."""
from typing import Literal
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Accepts either phone or email as username."""
    username: str = Field(..., description="Phone number or email address")
    password: str = Field(..., min_length=4)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Literal["officer", "farmer", "buyer"]
    user_id: int
    name: str


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str | None = Field(None, pattern=r"^\+?\d{7,15}$")
    email: str | None = None
    password: str = Field(..., min_length=6)
    role: Literal["officer", "farmer", "buyer"]
    village_id: str | None = None   # required for farmer
    buyer_id: str | None = None     # required for buyer
    language: Literal["en", "hi", "pa"] = "en"
