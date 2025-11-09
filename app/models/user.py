"""User model definitions."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr
    name: str


class UserCreate(UserBase):
    """User creation model with password."""

    password: str


class User(UserBase):
    """User model without password (for API responses)."""

    id: str = Field(alias="_id", serialization_alias="id")
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class UserInDB(User):
    """User model with hashed password (for database storage)."""

    hashed_password: str
