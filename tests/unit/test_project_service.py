"""Tests for ProjectService."""
import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId


@pytest.mark.asyncio
class TestProjectServiceCreate:
    """Tests for creating projects."""

    async def test_create_project_success(self):
        """Test successful project creation."""
        from app.services.project_service import ProjectService
        from app.models.project import ProjectCreate, ProjectFolder, ProjectType

        mock_db = MagicMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.return_value = mock_projects

        # No existing project with same slug
        mock_projects.find_one.return_value = None
        mock_projects.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = ProjectService(mock_db)
        project_data = ProjectCreate(
            title="Learn Rust",
            area="engineering",
        )

        project = await service.create_project(
            user_id="user123",
            project_create=project_data,
        )

        assert project.title == "Learn Rust"
        assert project.area == "engineering"
        assert project.slug == "learn-rust"
        assert project.folder == ProjectFolder.ACTIVE
        assert project.type == ProjectType.STANDARD
        assert project.deleted is False

    async def test_create_project_with_all_fields(self):
        """Test creating project with all optional fields."""
        from app.services.project_service import ProjectService
        from app.models.project import ProjectCreate, ProjectFolder, ProjectType

        mock_db = MagicMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.return_value = mock_projects

        mock_projects.find_one.return_value = None
        mock_projects.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = ProjectService(mock_db)
        due_date = date(2025, 12, 31)
        project_data = ProjectCreate(
            title="DE Shaw TPM Role",
            area="career",
            folder=ProjectFolder.INCUBATOR,
            type=ProjectType.STANDARD,
            due=due_date,
            content="## Notes\n- Research company",
        )

        project = await service.create_project(
            user_id="user123",
            project_create=project_data,
        )

        assert project.title == "DE Shaw TPM Role"
        assert project.slug == "de-shaw-tpm-role"
        assert project.folder == ProjectFolder.INCUBATOR
        assert project.due == due_date
        assert project.content == "## Notes\n- Research company"

    async def test_create_project_duplicate_slug(self):
        """Test creating project with duplicate slug adds suffix."""
        from app.services.project_service import ProjectService
        from app.models.project import ProjectCreate

        mock_db = MagicMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.return_value = mock_projects

        # First find_one returns existing project, second returns None
        mock_projects.find_one.side_effect = [
            {"slug": "learn-rust"},  # base slug exists
            None,  # learn-rust-2 doesn't exist
        ]
        mock_projects.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = ProjectService(mock_db)
        project_data = ProjectCreate(title="Learn Rust", area="engineering")

        project = await service.create_project(
            user_id="user123",
            project_create=project_data,
        )

        assert project.slug == "learn-rust-2"


@pytest.mark.asyncio
class TestProjectServiceList:
    """Tests for listing projects."""

    async def test_list_projects_all(self):
        """Test listing all projects for a user."""
        from app.services.project_service import ProjectService

        mock_db = MagicMock()
        mock_projects = MagicMock()
        mock_db.__getitem__.return_value = mock_projects

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": ObjectId(),
                "user_id": "user123",
                "title": "Project 1",
                "slug": "project-1",
                "area": "engineering",
                "folder": "active",
                "type": "standard",
                "content": "",
                "created": date.today(),
                "deleted": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "_id": ObjectId(),
                "user_id": "user123",
                "title": "Project 2",
                "slug": "project-2",
                "area": "career",
                "folder": "incubator",
                "type": "standard",
                "content": "",
                "created": date.today(),
                "deleted": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        ])
        mock_projects.find.return_value = mock_cursor

        service = ProjectService(mock_db)
        projects = await service.list_projects(user_id="user123")

        assert len(projects) == 2
        assert projects[0].title == "Project 1"
        assert projects[1].title == "Project 2"

    async def test_list_projects_filtered_by_folder(self):
        """Test listing projects filtered by folder."""
        from app.services.project_service import ProjectService

        mock_db = MagicMock()
        mock_projects = MagicMock()
        mock_db.__getitem__.return_value = mock_projects

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_projects.find.return_value = mock_cursor

        service = ProjectService(mock_db)
        await service.list_projects(user_id="user123", folder="active")

        # Verify find was called with folder filter
        call_args = mock_projects.find.call_args[0][0]
        assert call_args["folder"] == "active"
        assert call_args["deleted"] is False

    async def test_list_projects_filtered_by_area(self):
        """Test listing projects filtered by area."""
        from app.services.project_service import ProjectService

        mock_db = MagicMock()
        mock_projects = MagicMock()
        mock_db.__getitem__.return_value = mock_projects

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_projects.find.return_value = mock_cursor

        service = ProjectService(mock_db)
        await service.list_projects(user_id="user123", area="engineering")

        # Verify find was called with area filter
        call_args = mock_projects.find.call_args[0][0]
        assert call_args["area"] == "engineering"

    async def test_list_projects_excludes_deleted(self):
        """Test that deleted projects are excluded."""
        from app.services.project_service import ProjectService

        mock_db = MagicMock()
        mock_projects = MagicMock()
        mock_db.__getitem__.return_value = mock_projects

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_projects.find.return_value = mock_cursor

        service = ProjectService(mock_db)
        await service.list_projects(user_id="user123")

        # Verify deleted: False is in query
        call_args = mock_projects.find.call_args[0][0]
        assert call_args["deleted"] is False


@pytest.mark.asyncio
class TestProjectServiceGet:
    """Tests for getting a single project."""

    async def test_get_project_by_slug_found(self):
        """Test getting project by slug when it exists."""
        from app.services.project_service import ProjectService

        mock_db = MagicMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.return_value = mock_projects

        project_id = ObjectId()
        mock_projects.find_one.return_value = {
            "_id": project_id,
            "user_id": "user123",
            "title": "Learn Rust",
            "slug": "learn-rust",
            "area": "engineering",
            "folder": "active",
            "type": "standard",
            "content": "## Goals",
            "created": date.today(),
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        service = ProjectService(mock_db)
        project = await service.get_project_by_slug(
            user_id="user123",
            slug="learn-rust",
        )

        assert project.title == "Learn Rust"
        assert project.slug == "learn-rust"

    async def test_get_project_by_slug_not_found(self):
        """Test getting project by slug when it doesn't exist."""
        from app.services.project_service import ProjectService

        mock_db = MagicMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.return_value = mock_projects

        mock_projects.find_one.return_value = None

        service = ProjectService(mock_db)

        with pytest.raises(ValueError, match="Project not found"):
            await service.get_project_by_slug(
                user_id="user123",
                slug="nonexistent",
            )


@pytest.mark.asyncio
class TestProjectServiceUpdate:
    """Tests for updating projects."""

    async def test_update_project_content(self):
        """Test updating project content."""
        from app.services.project_service import ProjectService
        from app.models.project import ProjectUpdate

        mock_db = MagicMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.return_value = mock_projects

        project_id = ObjectId()
        existing_project = {
            "_id": project_id,
            "user_id": "user123",
            "title": "Learn Rust",
            "slug": "learn-rust",
            "area": "engineering",
            "folder": "active",
            "type": "standard",
            "content": "Old content",
            "created": date.today(),
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # find_one returns existing, find_one_and_update returns updated
        mock_projects.find_one.return_value = existing_project
        updated_project = existing_project.copy()
        updated_project["content"] = "New content"
        mock_projects.find_one_and_update.return_value = updated_project

        service = ProjectService(mock_db)
        update_data = ProjectUpdate(content="New content")

        project = await service.update_project(
            user_id="user123",
            slug="learn-rust",
            project_update=update_data,
        )

        assert project.content == "New content"

    async def test_update_project_title_changes_slug(self):
        """Test that updating title regenerates slug."""
        from app.services.project_service import ProjectService
        from app.models.project import ProjectUpdate

        mock_db = MagicMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.return_value = mock_projects

        project_id = ObjectId()
        existing_project = {
            "_id": project_id,
            "user_id": "user123",
            "title": "Learn Rust",
            "slug": "learn-rust",
            "area": "engineering",
            "folder": "active",
            "type": "standard",
            "content": "",
            "created": date.today(),
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # First find_one for get, then for slug check (returns None = no conflict)
        mock_projects.find_one.side_effect = [
            existing_project,
            None,  # new slug doesn't exist
        ]

        updated_project = existing_project.copy()
        updated_project["title"] = "Learn Python"
        updated_project["slug"] = "learn-python"
        mock_projects.find_one_and_update.return_value = updated_project

        service = ProjectService(mock_db)
        update_data = ProjectUpdate(title="Learn Python")

        project = await service.update_project(
            user_id="user123",
            slug="learn-rust",
            project_update=update_data,
        )

        assert project.title == "Learn Python"
        assert project.slug == "learn-python"


@pytest.mark.asyncio
class TestProjectServiceDelete:
    """Tests for soft-deleting projects."""

    async def test_delete_project_success(self):
        """Test soft-deleting a project."""
        from app.services.project_service import ProjectService

        mock_db = MagicMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.return_value = mock_projects

        existing_project = {
            "_id": ObjectId(),
            "user_id": "user123",
            "slug": "learn-rust",
            "deleted": False,
        }

        mock_projects.find_one.return_value = existing_project
        mock_projects.update_one.return_value = AsyncMock(modified_count=1)

        service = ProjectService(mock_db)
        result = await service.delete_project(
            user_id="user123",
            slug="learn-rust",
        )

        assert result["deleted_count"] == 1

    async def test_delete_project_not_found(self):
        """Test deleting non-existent project fails."""
        from app.services.project_service import ProjectService

        mock_db = MagicMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.return_value = mock_projects

        mock_projects.find_one.return_value = None

        service = ProjectService(mock_db)

        with pytest.raises(ValueError, match="Project not found"):
            await service.delete_project(
                user_id="user123",
                slug="nonexistent",
            )
