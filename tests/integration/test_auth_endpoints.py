"""Integration tests for auth endpoints."""
import pytest


@pytest.mark.asyncio
class TestAuthRegister:
    """Tests for POST /auth/register endpoint."""

    async def test_register_success(self, app_client):
        """Test successful user registration."""
        response = await app_client.post(
            "/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "name": "New User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert "id" in data
        assert "password" not in data
        assert "hashed_password" not in data

    async def test_register_duplicate_email(self, app_client):
        """Test registration with duplicate email returns 400."""
        # Register first user
        await app_client.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "password123",
                "name": "First User",
            },
        )

        # Try to register with same email
        response = await app_client.post(
            "/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "differentpassword",
                "name": "Second User",
            },
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_invalid_email(self, app_client):
        """Test registration with invalid email returns 422."""
        response = await app_client.post(
            "/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
                "name": "Test User",
            },
        )

        assert response.status_code == 422

    async def test_register_missing_fields(self, app_client):
        """Test registration with missing fields returns 422."""
        response = await app_client.post(
            "/auth/register",
            json={"email": "test@example.com"},
        )

        assert response.status_code == 422


@pytest.mark.asyncio
class TestAuthLogin:
    """Tests for POST /auth/login endpoint."""

    async def test_login_success(self, app_client):
        """Test successful login returns access token."""
        # Register user first
        await app_client.post(
            "/auth/register",
            json={
                "email": "loginuser@example.com",
                "password": "mypassword123",
                "name": "Login User",
            },
        )

        # Login
        response = await app_client.post(
            "/auth/login",
            json={
                "email": "loginuser@example.com",
                "password": "mypassword123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    async def test_login_wrong_password(self, app_client):
        """Test login with wrong password returns 401."""
        # Register user
        await app_client.post(
            "/auth/register",
            json={
                "email": "wrongpw@example.com",
                "password": "correctpassword",
                "name": "Test User",
            },
        )

        # Login with wrong password
        response = await app_client.post(
            "/auth/login",
            json={
                "email": "wrongpw@example.com",
                "password": "wrongpassword",
            },
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_login_nonexistent_user(self, app_client):
        """Test login with non-existent user returns 401."""
        response = await app_client.post(
            "/auth/login",
            json={
                "email": "notfound@example.com",
                "password": "somepassword",
            },
        )

        assert response.status_code == 401


@pytest.mark.asyncio
class TestAuthMe:
    """Tests for GET /auth/me endpoint."""

    async def test_get_current_user_authenticated(self, app_client):
        """Test getting current user with valid token."""
        # Register and login
        await app_client.post(
            "/auth/register",
            json={
                "email": "metest@example.com",
                "password": "password123",
                "name": "Me Test",
            },
        )

        login_response = await app_client.post(
            "/auth/login",
            json={
                "email": "metest@example.com",
                "password": "password123",
            },
        )

        token = login_response.json()["access_token"]

        # Get current user
        response = await app_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "metest@example.com"
        assert data["name"] == "Me Test"
        assert "id" in data

    async def test_get_current_user_no_token(self, app_client):
        """Test getting current user without token returns 401."""
        response = await app_client.get("/auth/me")

        assert response.status_code == 401

    async def test_get_current_user_invalid_token(self, app_client):
        """Test getting current user with invalid token returns 401."""
        response = await app_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401
