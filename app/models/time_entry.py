"""Time entry model definitions."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TimeEntryBase(BaseModel):
    """Base time entry fields."""

    project_slug: str
    description: str = ""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None


class TimeEntryCreate(BaseModel):
    """Time entry creation model."""

    project_slug: str
    description: str = ""
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None


class TimeEntryUpdate(BaseModel):
    """Time entry update model."""

    description: Optional[str] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None


class TimeEntry(TimeEntryBase):
    """Full time entry model with database fields."""

    id: str = Field(alias="_id", serialization_alias="id")
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}
