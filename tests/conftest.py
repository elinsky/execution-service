"""Pytest configuration and fixtures."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.config import settings


@pytest_asyncio.fixture
async def app_client():
    """
    Create a test client with a clean test database.

    This fixture:
    - Creates a test database connection
    - Yields an async HTTP client for testing
    - Cleans up the test database after each test
    """
    # Create test database client
    test_client = AsyncIOMotorClient(settings.mongodb_url)
    test_db_name = f"{settings.mongodb_db_name}_test"
    test_db = test_client[test_db_name]

    # Override the database dependency
    from app.database import database
    original_db = database.db
    database.db = test_db

    # Create HTTP client
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client

    # Cleanup: drop test database
    await test_client.drop_database(test_db_name)

    # Restore original database
    database.db = original_db
    test_client.close()
