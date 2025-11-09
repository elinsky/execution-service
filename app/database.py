"""MongoDB database connection using Motor (async driver)."""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings


class Database:
    """MongoDB database connection manager."""

    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None

    async def connect(self) -> None:
        """Connect to MongoDB Atlas."""
        self.client = AsyncIOMotorClient(settings.mongodb_url)
        self.db = self.client[settings.mongodb_db_name]
        print(f"Connected to MongoDB: {settings.mongodb_db_name}")

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            print("Disconnected from MongoDB")

    def get_collection(self, name: str):
        """Get a MongoDB collection."""
        if not self.db:
            raise RuntimeError("Database not connected")
        return self.db[name]


# Global database instance
database = Database()


async def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance."""
    if not database.db:
        raise RuntimeError("Database not connected")
    return database.db
