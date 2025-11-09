"""Action service - business logic for action management."""
from datetime import date, datetime
from typing import Optional
from bson import ObjectId

from app.models.action import Action, ActionCreate, ActionUpdate, ActionState


class ActionService:
    """Service for handling action operations."""

    def __init__(self, db):
        """Initialize service with database connection."""
        self.db = db
        self.actions = db["actions"]
        self.projects = db["projects"]

    def _doc_to_action(self, doc: dict) -> Action:
        """
        Convert database document to Action model.

        Handles datetime to date conversion for date fields.
        """
        return Action(
            _id=str(doc["_id"]),
            user_id=doc["user_id"],
            text=doc["text"],
            context=doc["context"],
            project_slug=doc.get("project_slug"),
            state=doc["state"],
            action_date=doc["action_date"].date() if isinstance(doc["action_date"], datetime) else doc["action_date"],
            due=doc["due"].date() if doc.get("due") and isinstance(doc["due"], datetime) else doc.get("due"),
            defer=doc["defer"].date() if doc.get("defer") and isinstance(doc["defer"], datetime) else doc.get("defer"),
            completed=doc["completed"].date() if doc.get("completed") and isinstance(doc["completed"], datetime) else doc.get("completed"),
            deleted=doc["deleted"],
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )

    async def create_action(
        self,
        user_id: str,
        action_create: ActionCreate,
    ) -> Action:
        """
        Create a new action.

        Args:
            user_id: User ID who owns the action
            action_create: Action creation data

        Returns:
            Created action object

        Raises:
            ValueError: If project doesn't exist when project_slug is provided
        """
        # Validate project if provided
        if action_create.project_slug:
            project = await self.projects.find_one({
                "user_id": user_id,
                "slug": action_create.project_slug,
                "deleted": False,
            })
            if not project:
                raise ValueError("Project not found")

        # Prepare action document
        now = datetime.utcnow()
        today = date.today()

        action_doc = {
            "user_id": user_id,
            "text": action_create.text,
            "context": action_create.context,
            "project_slug": action_create.project_slug,
            "state": ActionState.NEXT.value,
            "action_date": datetime.combine(today, datetime.min.time()),
            "deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        # Add optional fields (convert dates to datetime)
        if action_create.due:
            action_doc["due"] = datetime.combine(action_create.due, datetime.min.time())
        if action_create.defer:
            action_doc["defer"] = datetime.combine(action_create.defer, datetime.min.time())

        # Insert into database
        result = await self.actions.insert_one(action_doc)

        # Add _id to doc for conversion
        action_doc["_id"] = result.inserted_id

        # Return Action object using helper
        return self._doc_to_action(action_doc)

    async def list_actions(
        self,
        user_id: str,
        context: Optional[str] = None,
        project_slug: Optional[str] = None,
        state: Optional[str] = None,
    ) -> list[Action]:
        """
        List actions for a user with optional filtering.

        Args:
            user_id: User ID
            context: Optional context filter (e.g., @macbook)
            project_slug: Optional project filter
            state: Optional state filter

        Returns:
            List of actions
        """
        # Build query
        query = {
            "user_id": user_id,
            "deleted": False,
        }

        if context:
            query["context"] = context
        if project_slug:
            query["project_slug"] = project_slug
        if state:
            query["state"] = state

        # Execute query
        cursor = self.actions.find(query)
        action_docs = await cursor.to_list(length=None)

        # Convert to Action objects using helper
        return [self._doc_to_action(doc) for doc in action_docs]

    async def get_action_by_id(
        self,
        user_id: str,
        action_id: str,
    ) -> Action:
        """
        Get an action by ID.

        Args:
            user_id: User ID
            action_id: Action ID

        Returns:
            Action object

        Raises:
            ValueError: If action not found or invalid ID format
        """
        try:
            object_id = ObjectId(action_id)
        except Exception:
            raise ValueError("Invalid action ID format")

        action_doc = await self.actions.find_one({
            "_id": object_id,
            "user_id": user_id,
            "deleted": False,
        })

        if not action_doc:
            raise ValueError("Action not found")

        return self._doc_to_action(action_doc)

    async def update_action(
        self,
        user_id: str,
        action_id: str,
        action_update: ActionUpdate,
    ) -> Action:
        """
        Update an action.

        Args:
            user_id: User ID
            action_id: Action ID
            action_update: Update data

        Returns:
            Updated action object

        Raises:
            ValueError: If action not found or project doesn't exist
        """
        # Verify action exists
        try:
            object_id = ObjectId(action_id)
        except Exception:
            raise ValueError("Invalid action ID format")

        existing = await self.actions.find_one({
            "_id": object_id,
            "user_id": user_id,
            "deleted": False,
        })

        if not existing:
            raise ValueError("Action not found")

        # Validate project if being updated
        if action_update.project_slug is not None:
            project = await self.projects.find_one({
                "user_id": user_id,
                "slug": action_update.project_slug,
                "deleted": False,
            })
            if not project:
                raise ValueError("Project not found")

        # Build update document
        update_doc = {
            "updated_at": datetime.utcnow(),
        }

        # Add fields if provided
        if action_update.text is not None:
            update_doc["text"] = action_update.text
        if action_update.context is not None:
            update_doc["context"] = action_update.context
        if action_update.project_slug is not None:
            update_doc["project_slug"] = action_update.project_slug
        if action_update.state is not None:
            update_doc["state"] = action_update.state.value
        if action_update.due is not None:
            update_doc["due"] = datetime.combine(action_update.due, datetime.min.time())
        if action_update.defer is not None:
            update_doc["defer"] = datetime.combine(action_update.defer, datetime.min.time())

        # Update in database
        updated_doc = await self.actions.find_one_and_update(
            {"_id": object_id, "user_id": user_id, "deleted": False},
            {"$set": update_doc},
            return_document=True,
        )

        return self._doc_to_action(updated_doc)

    async def complete_action(
        self,
        user_id: str,
        action_id: str,
    ) -> Action:
        """
        Complete an action.

        Args:
            user_id: User ID
            action_id: Action ID

        Returns:
            Completed action object

        Raises:
            ValueError: If action not found
        """
        # Verify action exists
        try:
            object_id = ObjectId(action_id)
        except Exception:
            raise ValueError("Invalid action ID format")

        existing = await self.actions.find_one({
            "_id": object_id,
            "user_id": user_id,
            "deleted": False,
        })

        if not existing:
            raise ValueError("Action not found")

        # Complete the action
        today = date.today()
        update_doc = {
            "state": ActionState.COMPLETED.value,
            "completed": datetime.combine(today, datetime.min.time()),
            "updated_at": datetime.utcnow(),
        }

        updated_doc = await self.actions.find_one_and_update(
            {"_id": object_id, "user_id": user_id, "deleted": False},
            {"$set": update_doc},
            return_document=True,
        )

        return self._doc_to_action(updated_doc)

    async def delete_action(
        self,
        user_id: str,
        action_id: str,
    ) -> dict:
        """
        Soft delete an action.

        Args:
            user_id: User ID
            action_id: Action ID

        Returns:
            Dictionary with deleted_count

        Raises:
            ValueError: If action not found
        """
        # Verify action exists
        try:
            object_id = ObjectId(action_id)
        except Exception:
            raise ValueError("Invalid action ID format")

        existing = await self.actions.find_one({
            "_id": object_id,
            "user_id": user_id,
            "deleted": False,
        })

        if not existing:
            raise ValueError("Action not found")

        # Soft delete
        result = await self.actions.update_one(
            {"_id": object_id, "user_id": user_id},
            {"$set": {"deleted": True, "updated_at": datetime.utcnow()}},
        )

        return {"deleted_count": result.modified_count}
