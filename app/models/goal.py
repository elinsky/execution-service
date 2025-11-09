"""Goal model definitions (30k level)."""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class GoalBase(BaseModel):
    """Base goal fields."""

    title: str
    area: str
    content: str = ""


class GoalCreate(GoalBase):
    """Goal creation model."""

    pass


class GoalUpdate(BaseModel):
    """Goal update model - all fields optional."""

    title: Optional[str] = None
    area: Optional[str] = None
    content: Optional[str] = None


class Goal(GoalBase):
    """Full goal model with database fields."""

    id: str = Field(alias="_id", serialization_alias="id")
    user_id: str
    slug: str
    created: date
    last_reviewed: Optional[date] = None
    folder: str = "active"  # active or incubator
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}
