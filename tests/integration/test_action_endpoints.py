"""Integration tests for action endpoints."""
import pytest
from datetime import date
from httpx import AsyncClient


@pytest.mark.asyncio
class TestActionCreate:
    """Tests for creating actions."""

    async def test_create_action_success(self, app_client):
        """Test successful action creation."""
        # Register and login
        register_data = {
            "email": "test@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]

        # Create action
        action_data = {
            "text": "Review pull request",
            "context": "@macbook",
        }
        response = await app_client.post(
            "/actions",
            json=action_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["text"] == "Review pull request"
        assert data["context"] == "@macbook"
        assert data["state"] == "next"
        assert data["deleted"] is False
        assert "id" in data

    async def test_create_action_with_project(self, app_client):
        """Test creating action with project reference."""
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

        # Create project first
        project_data = {"title": "Learn Rust", "area": "engineering"}
        await app_client.post(
            "/projects",
            json=project_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Create action with project
        action_data = {
            "text": "Read chapter 3",
            "context": "@home",
            "project_slug": "learn-rust",
        }
        response = await app_client.post(
            "/actions",
            json=action_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["project_slug"] == "learn-rust"

    async def test_create_action_with_nonexistent_project(self, app_client):
        """Test creating action with invalid project fails."""
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

        # Create action with nonexistent project
        action_data = {
            "text": "Some action",
            "context": "@macbook",
            "project_slug": "nonexistent",
        }
        response = await app_client.post(
            "/actions",
            json=action_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400

    async def test_create_action_unauthenticated(self, app_client):
        """Test creating action without authentication fails."""
        action_data = {
            "text": "Test action",
            "context": "@macbook",
        }
        response = await app_client.post("/actions", json=action_data)

        assert response.status_code == 401


@pytest.mark.asyncio
class TestActionList:
    """Tests for listing actions."""

    async def test_list_actions_empty(self, app_client):
        """Test listing actions when none exist."""
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
            "/actions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_actions_with_data(self, app_client):
        """Test listing actions returns all user actions."""
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

        # Create two actions
        await app_client.post(
            "/actions",
            json={"text": "Action 1", "context": "@macbook"},
            headers={"Authorization": f"Bearer {token}"},
        )
        await app_client.post(
            "/actions",
            json={"text": "Action 2", "context": "@home"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # List actions
        response = await app_client.get(
            "/actions",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["text"] == "Action 1"
        assert data[1]["text"] == "Action 2"

    async def test_list_actions_filtered_by_context(self, app_client):
        """Test listing actions filtered by context."""
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

        # Create actions with different contexts
        await app_client.post(
            "/actions",
            json={"text": "Macbook Action", "context": "@macbook"},
            headers={"Authorization": f"Bearer {token}"},
        )
        await app_client.post(
            "/actions",
            json={"text": "Home Action", "context": "@home"},
            headers={"Authorization": f"Bearer {token}"},
        )

        # List only @macbook actions
        response = await app_client.get(
            "/actions?context=@macbook",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["text"] == "Macbook Action"

    async def test_list_actions_unauthenticated(self, app_client):
        """Test listing actions without authentication fails."""
        response = await app_client.get("/actions")
        assert response.status_code == 401


@pytest.mark.asyncio
class TestActionGet:
    """Tests for getting a single action."""

    async def test_get_action_by_id_success(self, app_client):
        """Test getting action by ID."""
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

        # Create action
        create_response = await app_client.post(
            "/actions",
            json={"text": "My Action", "context": "@macbook"},
            headers={"Authorization": f"Bearer {token}"},
        )
        action_id = create_response.json()["id"]

        # Get action
        response = await app_client.get(
            f"/actions/{action_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "My Action"
        assert data["id"] == action_id

    async def test_get_action_not_found(self, app_client):
        """Test getting non-existent action returns 404."""
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

        from bson import ObjectId

        fake_id = str(ObjectId())
        response = await app_client.get(
            f"/actions/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404


@pytest.mark.asyncio
class TestActionUpdate:
    """Tests for updating actions."""

    async def test_update_action_text(self, app_client):
        """Test updating action text."""
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

        # Create action
        create_response = await app_client.post(
            "/actions",
            json={"text": "Old text", "context": "@macbook"},
            headers={"Authorization": f"Bearer {token}"},
        )
        action_id = create_response.json()["id"]

        # Update text
        update_data = {"text": "New text"}
        response = await app_client.patch(
            f"/actions/{action_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "New text"


@pytest.mark.asyncio
class TestActionComplete:
    """Tests for completing actions."""

    async def test_complete_action_success(self, app_client):
        """Test completing an action."""
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

        # Create action
        create_response = await app_client.post(
            "/actions",
            json={"text": "To complete", "context": "@macbook"},
            headers={"Authorization": f"Bearer {token}"},
        )
        action_id = create_response.json()["id"]

        # Complete action
        response = await app_client.post(
            f"/actions/{action_id}/complete",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "completed"
        assert data["completed"] is not None


@pytest.mark.asyncio
class TestActionDelete:
    """Tests for deleting actions."""

    async def test_delete_action_success(self, app_client):
        """Test soft deleting an action."""
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

        # Create action
        create_response = await app_client.post(
            "/actions",
            json={"text": "To delete", "context": "@macbook"},
            headers={"Authorization": f"Bearer {token}"},
        )
        action_id = create_response.json()["id"]

        # Delete action
        response = await app_client.delete(
            f"/actions/{action_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 1

        # Verify action is not in list
        list_response = await app_client.get(
            "/actions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert len(list_response.json()) == 0

    async def test_delete_action_not_found(self, app_client):
        """Test deleting non-existent action returns 404."""
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

        from bson import ObjectId

        fake_id = str(ObjectId())
        response = await app_client.delete(
            f"/actions/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
