"""Project router - API endpoints for project management."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from app.database import get_database
from app.models.project import Project, ProjectCreate, ProjectUpdate
from app.routers.auth import get_current_user_id
from app.services.project_service import ProjectService


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Create a new project.

    Args:
        project: Project creation data
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Created project object

    Raises:
        HTTPException: If project creation fails (400)
    """
    service = ProjectService(db)

    try:
        created_project = await service.create_project(
            user_id=user_id,
            project_create=project,
        )
        return created_project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=list[Project])
async def list_projects(
    folder: Optional[str] = Query(None, description="Filter by folder"),
    area: Optional[str] = Query(None, description="Filter by area"),
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    List projects for the current user.

    Args:
        folder: Optional folder filter
        area: Optional area filter
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        List of projects
    """
    service = ProjectService(db)

    projects = await service.list_projects(
        user_id=user_id,
        folder=folder,
        area=area,
    )

    return projects


@router.get("/{slug}", response_model=Project)
async def get_project(
    slug: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Get a project by slug.

    Args:
        slug: Project slug
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Project object

    Raises:
        HTTPException: If project not found (404)
    """
    service = ProjectService(db)

    try:
        project = await service.get_project_by_slug(
            user_id=user_id,
            slug=slug,
        )
        return project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.patch("/{slug}", response_model=Project)
async def update_project(
    slug: str,
    project_update: ProjectUpdate,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Update a project.

    Args:
        slug: Project slug
        project_update: Update data
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Updated project object

    Raises:
        HTTPException: If project not found (404)
    """
    service = ProjectService(db)

    try:
        updated_project = await service.update_project(
            user_id=user_id,
            slug=slug,
            project_update=project_update,
        )
        return updated_project
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete("/{slug}")
async def delete_project(
    slug: str,
    user_id: str = Depends(get_current_user_id),
    db=Depends(get_database),
):
    """
    Soft delete a project.

    Args:
        slug: Project slug
        user_id: Current user ID (from token)
        db: Database connection

    Returns:
        Dictionary with deleted_count

    Raises:
        HTTPException: If project not found (404)
    """
    service = ProjectService(db)

    try:
        result = await service.delete_project(
            user_id=user_id,
            slug=slug,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
