"""Action model definitions."""
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ActionState(str, Enum):
    """Action states (matching todo.txt workflow)."""

    NEXT = "next"
    WAITING = "waiting"
    DEFERRED = "deferred"
    INCUBATING = "incubating"
    COMPLETED = "completed"


class ActionBase(BaseModel):
    """Base action fields."""

    text: str
    context: str  # e.g., @macbook, @home, @phone
    project_slug: Optional[str] = None
    state: ActionState = ActionState.NEXT
    due: Optional[date] = None
    defer: Optional[date] = None


class ActionCreate(BaseModel):
    """Action creation model."""

    text: str
    context: str
    project_slug: Optional[str] = None
    due: Optional[date] = None
    defer: Optional[date] = None


class ActionUpdate(BaseModel):
    """Action update model - all fields optional."""

    text: Optional[str] = None
    context: Optional[str] = None
    project_slug: Optional[str] = None
    state: Optional[ActionState] = None
    due: Optional[date] = None
    defer: Optional[date] = None


class Action(ActionBase):
    """Full action model with database fields."""

    id: str = Field(alias="_id", serialization_alias="id")
    user_id: str
    action_date: date  # Creation date
    completed: Optional[date] = None
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}
