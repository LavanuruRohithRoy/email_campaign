from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    org_id: UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime


class BootstrapRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = Field(default=None, max_length=255)


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool = True

    @field_validator("role")
    @classmethod
    def validate_assignable_role(cls, value: UserRole) -> UserRole:
        if value not in {UserRole.CAMPAIGN_MANAGER, UserRole.VIEWER}:
            raise ValueError("INVALID_ROLE_ASSIGNMENT")
        return value


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int
