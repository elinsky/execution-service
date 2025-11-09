"""Authentication service - business logic for user auth."""
from datetime import datetime
from bson import ObjectId

from app.models.user import User, UserInDB
from app.utils.auth import create_access_token, hash_password, verify_password


class AuthService:
    """Service for handling user authentication."""

    def __init__(self, db):
        """Initialize service with database connection."""
        self.db = db
        self.users = db["users"]

    async def register_user(self, email: str, password: str, name: str) -> User:
        """
        Register a new user.

        Args:
            email: User email address
            password: Plain text password
            name: User's name

        Returns:
            User object (without password)

        Raises:
            ValueError: If email is already registered
        """
        # Check if email already exists
        existing = await self.users.find_one({"email": email})
        if existing:
            raise ValueError("Email already registered")

        # Hash password
        hashed_password = hash_password(password)

        # Create user document
        now = datetime.utcnow()
        user_doc = {
            "email": email,
            "hashed_password": hashed_password,
            "name": name,
            "created_at": now,
            "updated_at": now,
        }

        # Insert into database
        result = await self.users.insert_one(user_doc)

        # Return User object (without hashed_password)
        return User(
            _id=str(result.inserted_id),
            email=email,
            name=name,
            created_at=now,
            updated_at=now,
        )

    async def login(self, email: str, password: str) -> str:
        """
        Login user and return JWT token.

        Args:
            email: User email
            password: Plain text password

        Returns:
            JWT access token

        Raises:
            ValueError: If credentials are invalid
        """
        # Find user by email
        user_doc = await self.users.find_one({"email": email})
        if not user_doc:
            raise ValueError("Invalid email or password")

        # Verify password
        if not verify_password(password, user_doc["hashed_password"]):
            raise ValueError("Invalid email or password")

        # Generate JWT token
        token = create_access_token(user_id=str(user_doc["_id"]))

        return token

    async def get_user_by_id(self, user_id: str) -> User:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User object

        Raises:
            ValueError: If user not found
        """
        try:
            object_id = ObjectId(user_id)
        except Exception:
            raise ValueError("Invalid user ID format")

        user_doc = await self.users.find_one({"_id": object_id})
        if not user_doc:
            raise ValueError("User not found")

        return User(
            _id=str(user_doc["_id"]),
            email=user_doc["email"],
            name=user_doc["name"],
            created_at=user_doc["created_at"],
            updated_at=user_doc["updated_at"],
        )
