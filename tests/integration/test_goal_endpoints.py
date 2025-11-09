"""Integration tests for goal endpoints."""
import pytest


@pytest.mark.asyncio
class TestGoalCreate:
    """Tests for creating goals."""

    async def test_create_goal_success(self, app_client):
        """Test successful goal creation."""
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

        # Create goal
        goal_data = {
            "title": "Become a Great Leader",
            "area": "Leadership",
            "content": "Focus on developing leadership skills",
        }
        response = await app_client.post(
            "/goals",
            json=goal_data,
            headers=headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Become a Great Leader"
        assert data["area"] == "Leadership"
        assert data["slug"] == "become-a-great-leader"
        assert data["folder"] == "active"
        assert data["deleted"] is False
        assert "id" in data

    async def test_create_goal_unauthenticated(self, app_client):
        """Test that creating goal requires authentication."""
        goal_data = {
            "title": "Test Goal",
            "area": "Leadership",
        }
        response = await app_client.post("/goals", json=goal_data)

        assert response.status_code == 401


@pytest.mark.asyncio
class TestGoalList:
    """Tests for listing goals."""

    async def test_list_goals_empty(self, app_client):
        """Test listing goals when user has none."""
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

        response = await app_client.get("/goals", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_list_goals_with_data(self, app_client):
        """Test listing goals with data."""
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

        # Create two goals
        await app_client.post(
            "/goals",
            json={"title": "Goal 1", "area": "Leadership"},
            headers=headers,
        )
        await app_client.post(
            "/goals",
            json={"title": "Goal 2", "area": "Health"},
            headers=headers,
        )

        response = await app_client.get("/goals", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    async def test_list_goals_filtered_by_area(self, app_client):
        """Test listing goals filtered by area."""
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

        # Create goals in different areas
        await app_client.post(
            "/goals",
            json={"title": "Leadership Goal", "area": "Leadership"},
            headers=headers,
        )
        await app_client.post(
            "/goals",
            json={"title": "Health Goal", "area": "Health"},
            headers=headers,
        )

        # Filter by Leadership area
        response = await app_client.get("/goals?area=Leadership", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["area"] == "Leadership"

    async def test_list_goals_unauthenticated(self, app_client):
        """Test that listing goals requires authentication."""
        response = await app_client.get("/goals")

        assert response.status_code == 401


@pytest.mark.asyncio
class TestGoalGet:
    """Tests for getting a single goal."""

    async def test_get_goal_by_slug_success(self, app_client):
        """Test getting a goal by slug."""
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

        # Create goal
        create_response = await app_client.post(
            "/goals",
            json={"title": "Test Goal", "area": "Leadership"},
            headers=headers,
        )
        slug = create_response.json()["slug"]

        # Get goal by slug
        response = await app_client.get(f"/goals/{slug}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == slug
        assert data["title"] == "Test Goal"

    async def test_get_goal_not_found(self, app_client):
        """Test getting non-existent goal returns 404."""
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

        response = await app_client.get("/goals/nonexistent", headers=headers)

        assert response.status_code == 404


@pytest.mark.asyncio
class TestGoalUpdate:
    """Tests for updating goals."""

    async def test_update_goal_content(self, app_client):
        """Test updating goal content."""
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

        # Create goal
        create_response = await app_client.post(
            "/goals",
            json={"title": "Test Goal", "area": "Leadership", "content": "Old content"},
            headers=headers,
        )
        slug = create_response.json()["slug"]

        # Update goal
        response = await app_client.patch(
            f"/goals/{slug}",
            json={"content": "New content"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "New content"

    async def test_update_goal_title_changes_slug(self, app_client):
        """Test that updating title changes the slug."""
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

        # Create goal
        create_response = await app_client.post(
            "/goals",
            json={"title": "Old Title", "area": "Leadership"},
            headers=headers,
        )
        old_slug = create_response.json()["slug"]

        # Update title
        response = await app_client.patch(
            f"/goals/{old_slug}",
            json={"title": "New Title"},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["slug"] == "new-title"
        assert data["slug"] != old_slug


@pytest.mark.asyncio
class TestGoalDelete:
    """Tests for deleting goals."""

    async def test_delete_goal_success(self, app_client):
        """Test deleting a goal."""
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

        # Create goal
        create_response = await app_client.post(
            "/goals",
            json={"title": "Test Goal", "area": "Leadership"},
            headers=headers,
        )
        slug = create_response.json()["slug"]

        # Delete goal
        response = await app_client.delete(f"/goals/{slug}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 1

        # Verify goal is gone
        get_response = await app_client.get(f"/goals/{slug}", headers=headers)
        assert get_response.status_code == 404

    async def test_delete_goal_not_found(self, app_client):
        """Test deleting non-existent goal returns 404."""
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

        response = await app_client.delete("/goals/nonexistent", headers=headers)

        assert response.status_code == 404
