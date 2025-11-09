"""Action router - API endpoints for action management."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from app.database import get_database
from app.models.action import Action, ActionCreate, ActionUpdate
from app.routers.auth import get_current_user_id
from app.services.action_service import ActionService


router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("", response_model=Action, status_code=status.HTTP_201_CREATED)
async def create_action(
    action: ActionCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Create a new action.

    Args:
        action: Action creation data
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Created action object

    Raises:
        HTTPException: If action creation fails (400)
    """
    service = ActionService(db)

    try:
        created_action = await service.create_action(
            user_id=user_id,
            action_create=action,
        )
        return created_action
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=list[Action])
async def list_actions(
    context: Optional[str] = Query(None, description="Filter by context"),
    project_slug: Optional[str] = Query(None, description="Filter by project"),
    state: Optional[str] = Query(None, description="Filter by state"),
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    List actions for the current user.

    Args:
        context: Optional context filter (e.g., @macbook)
        project_slug: Optional project filter
        state: Optional state filter
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        List of actions
    """
    service = ActionService(db)

    actions = await service.list_actions(
        user_id=user_id,
        context=context,
        project_slug=project_slug,
        state=state,
    )

    return actions


@router.get("/{action_id}", response_model=Action)
async def get_action(
    action_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Get an action by ID.

    Args:
        action_id: Action ID
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Action object

    Raises:
        HTTPException: If action not found (404)
    """
    service = ActionService(db)

    try:
        action = await service.get_action_by_id(
            user_id=user_id,
            action_id=action_id,
        )
        return action
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch("/{action_id}", response_model=Action)
async def update_action(
    action_id: str,
    action_update: ActionUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Update an action.

    Args:
        action_id: Action ID
        action_update: Update data
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Updated action object

    Raises:
        HTTPException: If action not found (404) or invalid project (400)
    """
    service = ActionService(db)

    try:
        updated_action = await service.update_action(
            user_id=user_id,
            action_id=action_id,
            action_update=action_update,
        )
        return updated_action
    except ValueError as e:
        # Could be "Action not found" or "Project not found"
        if "Action not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )


@router.post("/{action_id}/complete", response_model=Action)
async def complete_action(
    action_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Complete an action.

    Args:
        action_id: Action ID
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Completed action object

    Raises:
        HTTPException: If action not found (404)
    """
    service = ActionService(db)

    try:
        completed_action = await service.complete_action(
            user_id=user_id,
            action_id=action_id,
        )
        return completed_action
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{action_id}")
async def delete_action(
    action_id: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Soft delete an action.

    Args:
        action_id: Action ID
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Dictionary with deleted_count

    Raises:
        HTTPException: If action not found (404)
    """
    service = ActionService(db)

    try:
        result = await service.delete_action(
            user_id=user_id,
            action_id=action_id,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
