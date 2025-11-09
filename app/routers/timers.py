"""Timer endpoints - time tracking operations."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import get_database
from app.models.time_entry import TimeEntry, TimeEntryCreate, TimeEntryUpdate
from app.routers.auth import get_current_user_id
from app.services.timer_service import TimerService


router = APIRouter(prefix="/timers", tags=["timers"])


class TimerStart(BaseModel):
    """Request model for starting a timer."""

    project_slug: str
    description: str = ""
    start_time: Optional[datetime] = None


@router.post("/start", response_model=TimeEntry)
async def start_timer(
    timer_start: TimerStart,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Start a new timer.

    - Requires authentication
    - Only one timer can run at a time
    - Project must exist
    """
    service = TimerService(db)
    try:
        return await service.start_timer(
            user_id=user_id,
            project_slug=timer_start.project_slug,
            description=timer_start.description,
            start_time=timer_start.start_time,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop", response_model=TimeEntry)
async def stop_timer(
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Stop the currently running timer.

    - Requires authentication
    - Must have a running timer
    """
    service = TimerService(db)
    try:
        return await service.stop_timer(user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/current", response_model=TimeEntry)
async def get_current_timer(
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Get the currently running timer, if any.

    - Requires authentication
    - Returns 404 if no timer is running
    """
    service = TimerService(db)
    entry = await service.get_current_timer(user_id=user_id)

    if not entry:
        raise HTTPException(status_code=404, detail="No timer running")

    return entry


@router.get("", response_model=list[TimeEntry])
async def list_entries(
    project_slug: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    List time entries for the authenticated user.

    - Requires authentication
    - Optional filters: project_slug, start_date, end_date
    - Results sorted by start_time descending (most recent first)
    """
    service = TimerService(db)
    return await service.list_entries(
        user_id=user_id,
        project_slug=project_slug,
        start_date=start_date,
        end_date=end_date,
    )


@router.post("", response_model=TimeEntry)
async def create_entry(
    entry_create: TimeEntryCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Create a manual time entry.

    - Requires authentication
    - Project must exist
    - Duration is calculated if not provided
    """
    service = TimerService(db)
    try:
        return await service.create_entry(
            user_id=user_id,
            entry_create=entry_create,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{entry_id}", response_model=TimeEntry)
async def get_entry(
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Get a specific time entry by ID.

    - Requires authentication
    - User must own the entry
    """
    service = TimerService(db)
    try:
        # We can use update_entry logic to fetch, but let's add get method
        from bson import ObjectId

        entries = await service.list_entries(user_id=user_id)
        for entry in entries:
            if entry.id == entry_id:
                return entry

        raise HTTPException(status_code=404, detail="Time entry not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{entry_id}", response_model=TimeEntry)
async def update_entry(
    entry_id: str,
    entry_update: TimeEntryUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Update a time entry.

    - Requires authentication
    - User must own the entry
    """
    service = TimerService(db)
    try:
        return await service.update_entry(
            user_id=user_id,
            entry_id=entry_id,
            entry_update=entry_update,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{entry_id}")
async def delete_entry(
    entry_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Delete a time entry.

    - Requires authentication
    - User must own the entry
    - Hard delete (permanent)
    """
    service = TimerService(db)
    try:
        return await service.delete_entry(
            user_id=user_id,
            entry_id=entry_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
