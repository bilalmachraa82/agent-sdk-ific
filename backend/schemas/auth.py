"""
Pydantic schemas for authentication and authorization
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Request schemas
class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=255)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class TenantCreate(BaseModel):
    """Schema for creating a new tenant during registration."""
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    slug: str = Field(..., min_length=3, max_length=50, pattern="^[a-z0-9-]+$", description="URL-friendly identifier")
    nif: str = Field(..., min_length=9, max_length=9, pattern="^[0-9]{9}$", description="Portuguese NIF")
    max_users: Optional[int] = Field(5, ge=1, le=100, description="Maximum users for tenant")
    max_evfs_per_month: Optional[int] = Field(10, ge=1, le=1000, description="Maximum EVFs per month")


class PasswordChange(BaseModel):
    """Schema for changing password."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class TokenRefresh(BaseModel):
    """Schema for refreshing access token."""
    refresh_token: str


# Response schemas
class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until expiration


class UserResponse(BaseModel):
    """User information response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: Optional[str]
    role: str
    tenant_id: UUID
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]


class TenantResponse(BaseModel):
    """Tenant information response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    nif: str
    plan: str
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # user_id
    tenant_id: str
    email: str
    role: str
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp