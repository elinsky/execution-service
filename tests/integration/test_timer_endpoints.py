"""Integration tests for timer endpoints."""
import pytest
from datetime import datetime, timedelta


@pytest.mark.asyncio
class TestTimerStart:
    """Tests for starting a timer."""

    async def test_start_timer_success(self, app_client):
        """Test starting a timer successfully."""
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
        headers = {"Authorization": f"Bearer {token}"}

        # Create a project
        project_data = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data, headers=headers)

        # Start timer
        response = await app_client.post(
            "/timers/start",
            json={
                "project_slug": "learn-rust",
                "description": "Working on feature",
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_slug"] == "learn-rust"
        assert data["description"] == "Working on feature"
        assert data["end_time"] is None
        assert data["duration_minutes"] is None

    async def test_start_timer_with_running_timer(self, app_client):
        """Test starting timer when one is already running fails."""
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
        headers = {"Authorization": f"Bearer {token}"}

        # Create a project
        project_data = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data, headers=headers)

        # Start first timer
        await app_client.post(
            "/timers/start",
            json={"project_slug": "learn-rust"},
            headers=headers,
        )

        # Try to start second timer
        response = await app_client.post(
            "/timers/start",
            json={"project_slug": "learn-rust"},
            headers=headers,
        )

        assert response.status_code == 400
        assert "already running" in response.json()["detail"].lower()

    async def test_start_timer_with_invalid_project(self, app_client):
        """Test starting timer with non-existent project fails."""
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
        headers = {"Authorization": f"Bearer {token}"}

        response = await app_client.post(
            "/timers/start",
            json={"project_slug": "nonexistent"},
            headers=headers,
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    async def test_start_timer_requires_auth(self, app_client):
        """Test that starting timer requires authentication."""
        response = await app_client.post(
            "/timers/start",
            json={"project_slug": "learn-rust"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTimerStop:
    """Tests for stopping a timer."""

    async def test_stop_timer_success(self, app_client):
        """Test stopping a running timer."""
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
        headers = {"Authorization": f"Bearer {token}"}

        # Create a project
        project_data = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data, headers=headers)

        # Start timer
        await app_client.post(
            "/timers/start",
            json={"project_slug": "learn-rust"},
            headers=headers,
        )

        # Stop timer
        response = await app_client.post("/timers/stop", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["end_time"] is not None
        assert data["duration_minutes"] is not None

    async def test_stop_timer_no_running_timer(self, app_client):
        """Test stopping timer when none is running fails."""
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
        headers = {"Authorization": f"Bearer {token}"}

        response = await app_client.post("/timers/stop", headers=headers)

        assert response.status_code == 400
        assert "no timer" in response.json()["detail"].lower()

    async def test_stop_timer_requires_auth(self, app_client):
        """Test that stopping timer requires authentication."""
        response = await app_client.post("/timers/stop")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTimerGetCurrent:
    """Tests for getting current timer."""

    async def test_get_current_timer_found(self, app_client):
        """Test getting current running timer."""
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
        headers = {"Authorization": f"Bearer {token}"}

        # Create a project
        project_data = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data, headers=headers)

        # Start timer
        start_response = await app_client.post(
            "/timers/start",
            json={"project_slug": "learn-rust"},
            headers=headers,
        )

        # Get current timer
        response = await app_client.get("/timers/current", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == start_response.json()["id"]
        assert data["end_time"] is None

    async def test_get_current_timer_none(self, app_client):
        """Test getting current timer when none is running."""
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
        headers = {"Authorization": f"Bearer {token}"}

        response = await app_client.get("/timers/current", headers=headers)

        assert response.status_code == 404

    async def test_get_current_timer_requires_auth(self, app_client):
        """Test that getting current timer requires authentication."""
        response = await app_client.get("/timers/current")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTimerList:
    """Tests for listing time entries."""

    async def test_list_entries_all(self, app_client):
        """Test listing all time entries."""
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
        headers = {"Authorization": f"Bearer {token}"}

        # Create a project
        project_data = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data, headers=headers)

        # Create a completed entry
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow() - timedelta(hours=1)
        await app_client.post(
            "/timers",
            json={
                "project_slug": "learn-rust",
                "description": "Entry 1",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=headers,
        )

        response = await app_client.get("/timers", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    async def test_list_entries_filtered_by_project(self, app_client):
        """Test listing entries filtered by project."""
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
        headers = {"Authorization": f"Bearer {token}"}

        # Create two projects
        project_data1 = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data1, headers=headers)

        project_data2 = {"title": "Learn Python", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data2, headers=headers)

        # Create entries for different projects
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow() - timedelta(hours=1)

        await app_client.post(
            "/timers",
            json={
                "project_slug": "learn-rust",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=headers,
        )
        await app_client.post(
            "/timers",
            json={
                "project_slug": "learn-python",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=headers,
        )

        # Filter by first project
        response = await app_client.get(
            "/timers?project_slug=learn-rust", headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(entry["project_slug"] == "learn-rust" for entry in data)

    async def test_list_entries_requires_auth(self, app_client):
        """Test that listing entries requires authentication."""
        response = await app_client.get("/timers")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTimerCreate:
    """Tests for creating manual time entries."""

    async def test_create_entry_success(self, app_client):
        """Test creating a manual time entry."""
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
        headers = {"Authorization": f"Bearer {token}"}

        # Create a project
        project_data = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data, headers=headers)

        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()

        response = await app_client.post(
            "/timers",
            json={
                "project_slug": "learn-rust",
                "description": "Manual entry",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_minutes": 120,
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_slug"] == "learn-rust"
        assert data["description"] == "Manual entry"
        assert data["duration_minutes"] == 120

    async def test_create_entry_calculates_duration(self, app_client):
        """Test that duration is calculated if not provided."""
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
        headers = {"Authorization": f"Bearer {token}"}

        # Create a project
        project_data = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data, headers=headers)

        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()

        response = await app_client.post(
            "/timers",
            json={
                "project_slug": "learn-rust",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["duration_minutes"] is not None
        assert 119 <= data["duration_minutes"] <= 121

    async def test_create_entry_with_invalid_project(self, app_client):
        """Test creating entry with non-existent project fails."""
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
        headers = {"Authorization": f"Bearer {token}"}

        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()

        response = await app_client.post(
            "/timers",
            json={
                "project_slug": "nonexistent",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=headers,
        )

        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()

    async def test_create_entry_requires_auth(self, app_client):
        """Test that creating entry requires authentication."""
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()

        response = await app_client.post(
            "/timers",
            json={
                "project_slug": "learn-rust",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTimerUpdate:
    """Tests for updating time entries."""

    async def test_update_entry_success(self, app_client):
        """Test updating a time entry."""
        # Register and login
        register_data = {
            "email": "test13@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test13@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a project
        project_data = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data, headers=headers)

        # Create entry
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()
        create_response = await app_client.post(
            "/timers",
            json={
                "project_slug": "learn-rust",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=headers,
        )
        entry_id = create_response.json()["id"]

        # Update entry
        response = await app_client.patch(
            f"/timers/{entry_id}",
            json={"description": "Updated description"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated description"

    async def test_update_entry_not_found(self, app_client):
        """Test updating non-existent entry fails."""
        # Register and login
        register_data = {
            "email": "test14@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test14@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        from bson import ObjectId

        response = await app_client.patch(
            f"/timers/{str(ObjectId())}",
            json={"description": "Updated"},
            headers=headers,
        )

        assert response.status_code == 404

    async def test_update_entry_requires_auth(self, app_client):
        """Test that updating entry requires authentication."""
        from bson import ObjectId

        response = await app_client.patch(
            f"/timers/{str(ObjectId())}",
            json={"description": "Updated"},
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestTimerDelete:
    """Tests for deleting time entries."""

    async def test_delete_entry_success(self, app_client):
        """Test deleting a time entry."""
        # Register and login
        register_data = {
            "email": "test15@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test15@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create a project
        project_data = {"title": "Learn Rust", "area": "Learning", "folder": "active"}
        await app_client.post("/projects", json=project_data, headers=headers)

        # Create entry
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()
        create_response = await app_client.post(
            "/timers",
            json={
                "project_slug": "learn-rust",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            headers=headers,
        )
        entry_id = create_response.json()["id"]

        # Delete entry
        response = await app_client.delete(f"/timers/{entry_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 1

        # Verify entry is gone
        get_response = await app_client.get(f"/timers/{entry_id}", headers=headers)
        assert get_response.status_code == 404

    async def test_delete_entry_not_found(self, app_client):
        """Test deleting non-existent entry fails."""
        # Register and login
        register_data = {
            "email": "test16@example.com",
            "password": "password123",
            "name": "Test User",
        }
        await app_client.post("/auth/register", json=register_data)

        login_data = {"email": "test16@example.com", "password": "password123"}
        login_response = await app_client.post("/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        from bson import ObjectId

        response = await app_client.delete(
            f"/timers/{str(ObjectId())}", headers=headers
        )

        assert response.status_code == 404

    async def test_delete_entry_requires_auth(self, app_client):
        """Test that deleting entry requires authentication."""
        from bson import ObjectId

        response = await app_client.delete(f"/timers/{str(ObjectId())}")

        assert response.status_code == 401
