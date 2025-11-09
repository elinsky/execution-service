"""Drop all data for a specific user."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient

async def drop_user_data(mongodb_url: str, user_id: str):
    """Delete all documents for a user."""
    client = AsyncIOMotorClient(mongodb_url)
    db = client["execution_system"]
    
    # Delete all collections for this user
    collections = ["projects", "actions", "goals", "timers"]
    
    for collection_name in collections:
        collection = db[collection_name]
        result = await collection.delete_many({"user_id": user_id})
        print(f"Deleted {result.deleted_count} documents from {collection_name}")
    
    client.close()
    print("Done!")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python drop_user_data.py <mongodb_url> <user_id>")
        sys.exit(1)
    
    asyncio.run(drop_user_data(sys.argv[1], sys.argv[2]))
