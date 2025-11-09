"""Project model definitions."""
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProjectFolder(str, Enum):
    """Project folder locations."""

    ACTIVE = "active"
    INCUBATOR = "incubator"
    COMPLETED = "completed"
    DESCOPED = "descoped"


class ProjectType(str, Enum):
    """Project types."""

    STANDARD = "standard"
    COORDINATION = "coordination"
    HABIT = "habit"
    GOAL = "goal"


class ProjectBase(BaseModel):
    """Base project fields."""

    title: str
    area: str
    folder: ProjectFolder = ProjectFolder.ACTIVE
    type: ProjectType = ProjectType.STANDARD
    due: Optional[date] = None
    content: str = ""


class ProjectCreate(ProjectBase):
    """Project creation model."""

    pass


class ProjectUpdate(BaseModel):
    """Project update model - all fields optional."""

    title: Optional[str] = None
    area: Optional[str] = None
    folder: Optional[ProjectFolder] = None
    type: Optional[ProjectType] = None
    due: Optional[date] = None
    content: Optional[str] = None


class Project(ProjectBase):
    """Full project model with database fields."""

    id: str = Field(alias="_id", serialization_alias="id")
    user_id: str
    slug: str
    created: date
    started: Optional[date] = None
    last_reviewed: Optional[date] = None
    completed: Optional[date] = None
    descoped: Optional[date] = None
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}
