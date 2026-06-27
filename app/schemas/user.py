from pydantic import BaseModel, EmailStr


class SignupRequest(BaseModel):
    """Schema for user registration."""
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    """Schema for returning user profile data."""
    id: int
    name: str
    email: EmailStr

    class Config:
        from_attributes = True
