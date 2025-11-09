"""Debug script to check what content is stored in MongoDB."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient

async def check_content():
    client = AsyncIOMotorClient("mongodb+srv://execution_user:BJw9VNyDAyprTZYHe6hd@cluster0.wf7nrwm.mongodb.net/?appName=Cluster0")
    db = client["execution_system"]

    # Find the machine learning project
    project = await db.projects.find_one({
        "slug": "machine-learning-skills-refresh",
        "user_id": "6911131d956adeac5dc51198"
    })

    if project:
        content = project.get("content", "")
        print("Content stored in DB:")
        print(repr(content[:200]))  # Show first 200 chars with escape sequences visible
        print("\n\nFirst 10 chars as bytes:")
        print([ord(c) for c in content[:10]])
    else:
        print("Project not found")

    client.close()

if __name__ == "__main__":
    asyncio.run(check_content())