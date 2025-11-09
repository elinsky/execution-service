"""Tests for AuthService."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId


@pytest.mark.asyncio
class TestAuthServiceRegister:
    """Tests for user registration."""

    async def test_register_user_success(self):
        """Test successful user registration."""
        from app.services.auth_service import AuthService

        # Mock database
        mock_db = MagicMock()
        mock_users = AsyncMock()
        mock_db.__getitem__.return_value = mock_users

        # No existing user
        mock_users.find_one.return_value = None

        # Mock insert result
        mock_users.insert_one.return_value = AsyncMock(inserted_id="user123")

        service = AuthService(mock_db)
        user = await service.register_user(
            email="brian@example.com",
            password="securepassword123",
            name="Brian"
        )

        assert user.email == "brian@example.com"
        assert user.name == "Brian"
        assert hasattr(user, "id")
        assert not hasattr(user, "hashed_password")  # Should not expose password

        # Verify database calls
        mock_users.find_one.assert_called_once()
        mock_users.insert_one.assert_called_once()

    async def test_register_duplicate_email(self):
        """Test registration with duplicate email fails."""
        from app.services.auth_service import AuthService

        # Mock database with existing user
        mock_db = MagicMock()
        mock_users = AsyncMock()
        mock_db.__getitem__.return_value = mock_users

        mock_users.find_one.return_value = {
            "_id": "existing123",
            "email": "brian@example.com"
        }

        service = AuthService(mock_db)

        with pytest.raises(ValueError, match="Email already registered"):
            await service.register_user(
                email="brian@example.com",
                password="password123",
                name="Brian"
            )

    async def test_register_hashes_password(self):
        """Test that password is hashed before storing."""
        from app.services.auth_service import AuthService

        mock_db = MagicMock()
        mock_users = AsyncMock()
        mock_db.__getitem__.return_value = mock_users

        mock_users.find_one.return_value = None
        mock_users.insert_one.return_value = AsyncMock(inserted_id="user123")

        service = AuthService(mock_db)
        await service.register_user(
            email="brian@example.com",
            password="plaintext",
            name="Brian"
        )

        # Verify insert_one was called with hashed password
        insert_call = mock_users.insert_one.call_args[0][0]
        assert "hashed_password" in insert_call
        assert insert_call["hashed_password"] != "plaintext"
        assert insert_call["hashed_password"].startswith("$2b$")


@pytest.mark.asyncio
class TestAuthServiceLogin:
    """Tests for user login."""

    async def test_login_success(self):
        """Test successful login returns token."""
        from app.services.auth_service import AuthService
        from app.utils.auth import hash_password

        mock_db = MagicMock()
        mock_users = AsyncMock()
        mock_db.__getitem__.return_value = mock_users

        # Mock existing user with hashed password
        hashed = hash_password("correctpassword")
        mock_users.find_one.return_value = {
            "_id": "user123",
            "email": "brian@example.com",
            "name": "Brian",
            "hashed_password": hashed,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        service = AuthService(mock_db)
        token = await service.login(
            email="brian@example.com",
            password="correctpassword"
        )

        assert isinstance(token, str)
        assert len(token) > 0

    async def test_login_user_not_found(self):
        """Test login with non-existent user fails."""
        from app.services.auth_service import AuthService

        mock_db = MagicMock()
        mock_users = AsyncMock()
        mock_db.__getitem__.return_value = mock_users

        mock_users.find_one.return_value = None

        service = AuthService(mock_db)

        with pytest.raises(ValueError, match="Invalid email or password"):
            await service.login(
                email="notfound@example.com",
                password="password123"
            )

    async def test_login_wrong_password(self):
        """Test login with incorrect password fails."""
        from app.services.auth_service import AuthService
        from app.utils.auth import hash_password

        mock_db = MagicMock()
        mock_users = AsyncMock()
        mock_db.__getitem__.return_value = mock_users

        hashed = hash_password("correctpassword")
        mock_users.find_one.return_value = {
            "_id": "user123",
            "email": "brian@example.com",
            "hashed_password": hashed,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        service = AuthService(mock_db)

        with pytest.raises(ValueError, match="Invalid email or password"):
            await service.login(
                email="brian@example.com",
                password="wrongpassword"
            )


@pytest.mark.asyncio
class TestAuthServiceGetUser:
    """Tests for getting user by ID."""

    async def test_get_user_by_id_found(self):
        """Test getting user by ID when user exists."""
        from app.services.auth_service import AuthService

        mock_db = MagicMock()
        mock_users = AsyncMock()
        mock_db.__getitem__.return_value = mock_users

        mock_users.find_one.return_value = {
            "_id": "user123",
            "email": "brian@example.com",
            "name": "Brian",
            "hashed_password": "$2b$12$...",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        service = AuthService(mock_db)
        user = await service.get_user_by_id("user123")

        assert user.id == "user123"
        assert user.email == "brian@example.com"
        assert user.name == "Brian"

    async def test_get_user_by_id_not_found(self):
        """Test getting user by ID when user doesn't exist."""
        from app.services.auth_service import AuthService

        mock_db = MagicMock()
        mock_users = AsyncMock()
        mock_db.__getitem__.return_value = mock_users

        mock_users.find_one.return_value = None

        service = AuthService(mock_db)

        with pytest.raises(ValueError, match="User not found"):
            await service.get_user_by_id("nonexistent")
