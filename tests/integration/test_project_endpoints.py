"""Integration tests for project endpoints."""
import pytest
from datetime import date
from httpx import AsyncClient


@pytest.mark.asyncio
class TestProjectCreate:
    """Tests for creating projects."""

    async def test_create_project_success(self, app_client):
        """Test successful project creation."""
        # First register and login
        register_data = {
            "email": "test@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create project
        project_data = {
            "title": "Learn Rust",
            "area": "engineering",
        }
        response = await app_client.post(
            "/projects",
            json=project_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Learn Rust"
        assert data["area"] == "engineering"
        assert data["slug"] == "learn-rust"
        assert data["folder"] == "active"
        assert data["type"] == "standard"
        assert data["deleted"] is False
        assert "id" in data
        assert "created" in data

    async def test_create_project_with_all_fields(self, app_client):
        """Test creating project with all optional fields."""
        # Register and login
        register_data = {
            "email": "test2@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test2@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create project with all fields
        project_data = {
            "title": "DE Shaw TPM Role",
            "area": "career",
            "folder": "incubator",
            "type": "standard",
            "due": "2025-12-31",
            "content": "## Notes\n- Research company",
        }
        response = await app_client.post(
            "/projects",
            json=project_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "DE Shaw TPM Role"
        assert data["slug"] == "de-shaw-tpm-role"
        assert data["folder"] == "incubator"
        assert data["due"] == "2025-12-31"
        assert data["content"] == "## Notes\n- Research company"

    async def test_create_project_unauthenticated(self, app_client):
        """Test creating project without authentication fails."""
        project_data = {
            "title": "Test Project",
            "area": "engineering",
        }
        response = await app_client.post("/projects", json=project_data)

        assert response.status_code == 401

    async def test_create_project_duplicate_slug(self, app_client):
        """Test creating projects with duplicate titles creates unique slugs."""
        # Register and login
        register_data = {
            "email": "test3@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test3@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create first project
        project_data = {"title": "Learn Rust", "area": "engineering"}
        response1 = await app_client.post(
            "/projects",
            json=project_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response1.status_code == 201
        assert response1.json()["slug"] == "learn-rust"

        # Create second project with same title
        response2 = await app_client.post(
            "/projects",
            json=project_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response2.status_code == 201
        assert response2.json()["slug"] == "learn-rust-2"


@pytest.mark.asyncio
class TestProjectList:
    """Tests for listing projects."""

    async def test_list_projects_empty(self, app_client):
        """Test listing projects when none exist."""
        # Register and login
        register_data = {
            "email": "test4@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test4@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        response = await app_client.get(
            "/projects",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_projects_with_data(self, app_client):
        """Test listing projects returns all user projects."""
        # Register and login
        register_data = {
            "email": "test5@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test5@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create two projects
        await app_client.post(
            "/projects",
            json={"title": "Project 1", "area": "engineering"},
            headers={"Authorization": f"Bearer {token}"},
        )
        await app_client.post(
            "/projects",
            json={"title": "Project 2", "area": "career"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # List projects
        response = await app_client.get(
            "/projects",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] == "Project 1"
        assert data[1]["title"] == "Project 2"

    async def test_list_projects_filtered_by_folder(self, app_client):
        """Test listing projects filtered by folder."""
        # Register and login
        register_data = {
            "email": "test6@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test6@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create projects in different folders
        await app_client.post(
            "/projects",
            json={"title": "Active Project", "area": "engineering", "folder": "active"},
            headers={"Authorization": f"Bearer {token}"},
        )
        await app_client.post(
            "/projects",
            json={
                "title": "Incubator Project",
                "area": "engineering",
                "folder": "incubator",
            },
            headers={"Authorization": f"Bearer {token}"},
        )

        # List only active projects
        response = await app_client.get(
            "/projects?folder=active",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Active Project"

    async def test_list_projects_unauthenticated(self, app_client):
        """Test listing projects without authentication fails."""
        response = await app_client.get("/projects")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestProjectGet:
    """Tests for getting a single project."""

    async def test_get_project_by_slug_success(self, app_client):
        """Test getting project by slug."""
        # Register and login
        register_data = {
            "email": "test7@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test7@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create project
        await app_client.post(
            "/projects",
            json={"title": "My Project", "area": "engineering"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Get project
        response = await app_client.get(
            "/projects/my-project",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "My Project"
        assert data["slug"] == "my-project"

    async def test_get_project_not_found(self, app_client):
        """Test getting non-existent project returns 404."""
        # Register and login
        register_data = {
            "email": "test8@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test8@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        response = await app_client.get(
            "/projects/nonexistent",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestProjectUpdate:
    """Tests for updating projects."""

    async def test_update_project_content(self, app_client):
        """Test updating project content."""
        # Register and login
        register_data = {
            "email": "test9@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test9@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create project
        await app_client.post(
            "/projects",
            json={"title": "Test Project", "area": "engineering"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Update content
        update_data = {"content": "## New Content\n- Task 1"}
        response = await app_client.patch(
            "/projects/test-project",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "## New Content\n- Task 1"

    async def test_update_project_title_changes_slug(self, app_client):
        """Test updating project title regenerates slug."""
        # Register and login
        register_data = {
            "email": "test10@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test10@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create project
        await app_client.post(
            "/projects",
            json={"title": "Old Title", "area": "engineering"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Update title
        update_data = {"title": "New Title"}
        response = await app_client.patch(
            "/projects/old-title",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["slug"] == "new-title"


@pytest.mark.asyncio
class TestProjectDelete:
    """Tests for deleting projects."""

    async def test_delete_project_success(self, app_client):
        """Test soft deleting a project."""
        # Register and login
        register_data = {
            "email": "test11@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test11@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create project
        await app_client.post(
            "/projects",
            json={"title": "To Delete", "area": "engineering"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # Delete project
        response = await app_client.delete(
            "/projects/to-delete",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 1

        # Verify project is not in list
        list_response = await app_client.get(
            "/projects",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(list_response.json()) == 0

    async def test_delete_project_not_found(self, app_client):
        """Test deleting non-existent project returns 404."""
        # Register and login
        register_data = {
            "email": "test12@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test12@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        response = await app_client.delete(
            "/projects/nonexistent",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
