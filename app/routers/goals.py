"""Goal router - API endpoints for goal management (30k level)."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from app.database import get_database
from app.models.goal import Goal, GoalCreate, GoalUpdate
from app.routers.auth import get_current_user_id
from app.services.goal_service import GoalService


router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=Goal, status_code=status.HTTP_201_CREATED)
async def create_goal(
    goal: GoalCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Create a new goal.

    - Requires authentication
    - Generates unique slug from title
    - Starts in active folder
    """
    service = GoalService(db)
    return await service.create_goal(user_id=user_id, goal_create=goal)


@router.get("", response_model=list[Goal])
async def list_goals(
    folder: Optional[str] = Query(None, description="Filter by folder (active, incubator)"),
    area: Optional[str] = Query(None, description="Filter by area"),
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    List goals for the authenticated user.

    - Requires authentication
    - Optional filters: folder, area
    - Excludes deleted goals
    """
    service = GoalService(db)
    return await service.list_goals(
        user_id=user_id,
        folder=folder,
        area=area,
    )


@router.get("/{slug}", response_model=Goal)
async def get_goal(
    slug: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Get a single goal by slug.

    - Requires authentication
    - Returns 404 if goal not found or deleted
    """
    service = GoalService(db)
    try:
        return await service.get_goal_by_slug(user_id=user_id, slug=slug)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{slug}", response_model=Goal)
async def update_goal(
    slug: str,
    goal_update: GoalUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Update a goal.

    - Requires authentication
    - If title is updated, slug is regenerated
    - Returns 404 if goal not found
    """
    service = GoalService(db)
    try:
        return await service.update_goal(
            user_id=user_id,
            slug=slug,
            goal_update=goal_update,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{slug}")
async def delete_goal(
    slug: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Soft delete a goal.

    - Requires authentication
    - Marks goal as deleted, doesn't remove from database
    - Returns 404 if goal not found
    """
    service = GoalService(db)
    try:
        return await service.delete_goal(user_id=user_id, slug=slug)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
