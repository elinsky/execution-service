"""Tests for auth utility functions."""
import pytest
from datetime import datetime, timedelta


class TestPasswordHashing:
    """Tests for password hashing functions."""

    def test_hash_password(self):
        """Test password hashing."""
        from app.utils.auth import hash_password

        password = "mysecretpassword123"
        hashed = hash_password(password)

        # Should return a bcrypt hash
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

        # Same password should produce different hashes (due to salt)
        hashed2 = hash_password(password)
        assert hashed != hashed2

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        from app.utils.auth import hash_password, verify_password

        password = "mysecretpassword123"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        from app.utils.auth import hash_password, verify_password

        password = "mysecretpassword123"
        hashed = hash_password(password)

        assert verify_password("wrongpassword", hashed) is False

    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        from app.utils.auth import hash_password, verify_password

        password = "mysecretpassword123"
        hashed = hash_password(password)

        assert verify_password("", hashed) is False


class TestJWTTokens:
    """Tests for JWT token functions."""

    def test_create_access_token_basic(self):
        """Test creating a basic JWT access token."""
        from app.utils.auth import create_access_token

        user_id = "user123"
        token = create_access_token(user_id=user_id)

        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_with_expiration(self):
        """Test creating a token with custom expiration."""
        from app.utils.auth import create_access_token

        user_id = "user123"
        token = create_access_token(user_id=user_id, expires_delta=timedelta(hours=1))

        assert isinstance(token, str)

    def test_verify_access_token_valid(self):
        """Test verifying a valid access token."""
        from app.utils.auth import create_access_token, verify_access_token

        user_id = "user123"
        token = create_access_token(user_id=user_id)

        decoded_user_id = verify_access_token(token)
        assert decoded_user_id == user_id

    def test_verify_access_token_invalid(self):
        """Test verifying an invalid token."""
        from app.utils.auth import verify_access_token

        invalid_token = "invalid.token.here"

        with pytest.raises(Exception):
            verify_access_token(invalid_token)

    def test_verify_access_token_expired(self):
        """Test verifying an expired token."""
        from app.utils.auth import create_access_token, verify_access_token

        user_id = "user123"
        # Create token that expires immediately
        token = create_access_token(user_id=user_id, expires_delta=timedelta(seconds=-1))

        with pytest.raises(Exception):
            verify_access_token(token)

    def test_token_contains_user_id(self):
        """Test that token payload contains user_id."""
        from app.utils.auth import create_access_token
        from jose import jwt
        from app.config import settings

        user_id = "user123"
        token = create_access_token(user_id=user_id)

        # Decode without verification to inspect payload
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

        assert "sub" in payload
        assert payload["sub"] == user_id
        assert "exp" in payload

    def test_different_users_different_tokens(self):
        """Test that different users get different tokens."""
        from app.utils.auth import create_access_token

        token1 = create_access_token(user_id="user1")
        token2 = create_access_token(user_id="user2")

        assert token1 != token2
