"""Goal service - business logic for goal management (30k level)."""
from datetime import date, datetime
from typing import Optional
from bson import ObjectId

from app.models.goal import Goal, GoalCreate, GoalUpdate
from app.utils.slug import slugify, generate_unique_slug


class GoalService:
    """Service for handling goal operations."""

    def __init__(self, db):
        """Initialize service with database connection."""
        self.db = db
        self.goals = db["goals"]

    def _doc_to_goal(self, doc: dict) -> Goal:
        """
        Convert database document to Goal model.

        Handles datetime to date conversion for date fields.
        """
        return Goal(
            _id=str(doc["_id"]),
            user_id=doc["user_id"],
            title=doc["title"],
            slug=doc["slug"],
            area=doc["area"],
            content=doc.get("content", ""),
            created=doc["created"].date() if isinstance(doc["created"], datetime) else doc["created"],
            last_reviewed=doc["last_reviewed"].date() if doc.get("last_reviewed") and isinstance(doc["last_reviewed"], datetime) else doc.get("last_reviewed"),
            folder=doc.get("folder", "active"),
            deleted=doc["deleted"],
            deleted_at=doc.get("deleted_at"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )

    async def create_goal(
        self,
        user_id: str,
        goal_create: GoalCreate,
    ) -> Goal:
        """
        Create a new goal.

        Args:
            user_id: User ID who owns the goal
            goal_create: Goal creation data

        Returns:
            Created goal object

        Raises:
            ValueError: If goal creation fails
        """
        # Generate unique slug
        base_slug = slugify(goal_create.title)
        slug = await generate_unique_slug(
            self.goals,
            base_slug,
            user_id=user_id,
        )

        # Prepare goal document
        now = datetime.utcnow()
        today = date.today()

        goal_doc = {
            "user_id": user_id,
            "title": goal_create.title,
            "slug": slug,
            "area": goal_create.area,
            "content": goal_create.content if goal_create.content else "",
            "created": datetime.combine(today, datetime.min.time()),
            "last_reviewed": None,
            "folder": "active",
            "deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        # Insert into database
        result = await self.goals.insert_one(goal_doc)

        # Add _id to doc for conversion
        goal_doc["_id"] = result.inserted_id

        # Return Goal object using helper
        return self._doc_to_goal(goal_doc)

    async def list_goals(
        self,
        user_id: str,
        folder: Optional[str] = None,
        area: Optional[str] = None,
    ) -> list[Goal]:
        """
        List goals for a user with optional filtering.

        Args:
            user_id: User ID
            folder: Optional folder filter (active, incubator)
            area: Optional area filter

        Returns:
            List of goals
        """
        # Build query
        query = {
            "user_id": user_id,
            "deleted": False,
        }

        if folder:
            query["folder"] = folder
        if area:
            query["area"] = area

        # Execute query
        cursor = self.goals.find(query)
        goal_docs = await cursor.to_list(length=None)

        # Convert to Goal objects
        return [self._doc_to_goal(doc) for doc in goal_docs]

    async def get_goal_by_slug(
        self,
        user_id: str,
        slug: str,
    ) -> Goal:
        """
        Get a single goal by slug.

        Args:
            user_id: User ID
            slug: Goal slug

        Returns:
            Goal object

        Raises:
            ValueError: If goal not found
        """
        goal_doc = await self.goals.find_one({
            "user_id": user_id,
            "slug": slug,
            "deleted": False,
        })

        if not goal_doc:
            raise ValueError("Goal not found")

        return self._doc_to_goal(goal_doc)

    async def update_goal(
        self,
        user_id: str,
        slug: str,
        goal_update: GoalUpdate,
    ) -> Goal:
        """
        Update a goal.

        Args:
            user_id: User ID
            slug: Goal slug
            goal_update: Update data

        Returns:
            Updated goal

        Raises:
            ValueError: If goal not found
        """
        # Verify goal exists
        existing = await self.goals.find_one({
            "user_id": user_id,
            "slug": slug,
            "deleted": False,
        })

        if not existing:
            raise ValueError("Goal not found")

        # Build update document
        update_doc = {
            "updated_at": datetime.utcnow(),
        }

        # Handle title change (regenerate slug)
        if goal_update.title is not None:
            update_doc["title"] = goal_update.title
            base_slug = slugify(goal_update.title)
            new_slug = await generate_unique_slug(
                self.goals,
                base_slug,
                user_id=user_id,
                exclude_id=existing["_id"],
            )
            update_doc["slug"] = new_slug

        if goal_update.area is not None:
            update_doc["area"] = goal_update.area
        if goal_update.content is not None:
            update_doc["content"] = goal_update.content

        # Update in database
        updated_doc = await self.goals.find_one_and_update(
            {"user_id": user_id, "slug": slug, "deleted": False},
            {"$set": update_doc},
            return_document=True,
        )

        return self._doc_to_goal(updated_doc)

    async def delete_goal(
        self,
        user_id: str,
        slug: str,
    ) -> dict:
        """
        Soft delete a goal.

        Args:
            user_id: User ID
            slug: Goal slug

        Returns:
            Dictionary with deleted_count

        Raises:
            ValueError: If goal not found
        """
        # Verify goal exists
        existing = await self.goals.find_one({
            "user_id": user_id,
            "slug": slug,
            "deleted": False,
        })

        if not existing:
            raise ValueError("Goal not found")

        # Soft delete
        result = await self.goals.update_one(
            {"user_id": user_id, "slug": slug},
            {
                "$set": {
                    "deleted": True,
                    "deleted_at": datetime.utcnow(),
                }
            },
        )

        return {"deleted_count": result.modified_count}
