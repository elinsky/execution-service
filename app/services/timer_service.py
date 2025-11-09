"""Timer service - business logic for time tracking."""
from datetime import datetime
from typing import Optional
from bson import ObjectId

from app.models.time_entry import TimeEntry, TimeEntryCreate, TimeEntryUpdate


class TimerService:
    """Service for handling time tracking operations."""

    def __init__(self, db):
        """Initialize service with database connection."""
        self.db = db
        self.time_entries = db["time_entries"]
        self.projects = db["projects"]

    def _doc_to_entry(self, doc: dict) -> TimeEntry:
        """
        Convert database document to TimeEntry model.
        """
        return TimeEntry(
            _id=str(doc["_id"]),
            user_id=doc["user_id"],
            project_slug=doc["project_slug"],
            description=doc.get("description", ""),
            start_time=doc["start_time"],
            end_time=doc.get("end_time"),
            duration_minutes=doc.get("duration_minutes"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )

    def _calculate_duration(self, start_time: datetime, end_time: datetime) -> int:
        """
        Calculate duration in minutes between start and end time.

        Args:
            start_time: Start time
            end_time: End time

        Returns:
            Duration in minutes
        """
        delta = end_time - start_time
        return int(delta.total_seconds() / 60)

    async def start_timer(
        self,
        user_id: str,
        project_slug: str,
        description: str = "",
        start_time: Optional[datetime] = None,
    ) -> TimeEntry:
        """
        Start a new timer.

        Args:
            user_id: User ID
            project_slug: Project slug
            description: Optional description
            start_time: Optional start time (defaults to now)

        Returns:
            Created time entry

        Raises:
            ValueError: If timer already running or project doesn't exist
        """
        # Check if timer is already running
        running_timer = await self.time_entries.find_one({
            "user_id": user_id,
            "end_time": None,
        })

        if running_timer:
            raise ValueError("Timer already running")

        # Validate project exists
        project = await self.projects.find_one({
            "user_id": user_id,
            "slug": project_slug,
            "deleted": False,
        })

        if not project:
            raise ValueError("Project not found")

        # Create time entry
        now = datetime.utcnow()
        if start_time is None:
            start_time = now

        entry_doc = {
            "user_id": user_id,
            "project_slug": project_slug,
            "description": description,
            "start_time": start_time,
            "end_time": None,
            "duration_minutes": None,
            "created_at": now,
            "updated_at": now,
        }

        result = await self.time_entries.insert_one(entry_doc)
        entry_doc["_id"] = result.inserted_id

        return self._doc_to_entry(entry_doc)

    async def stop_timer(
        self,
        user_id: str,
        end_time: Optional[datetime] = None,
    ) -> TimeEntry:
        """
        Stop the currently running timer.

        Args:
            user_id: User ID
            end_time: Optional end time (defaults to now)

        Returns:
            Updated time entry with end_time and duration

        Raises:
            ValueError: If no timer is running
        """
        # Find running timer
        running_timer = await self.time_entries.find_one({
            "user_id": user_id,
            "end_time": None,
        })

        if not running_timer:
            raise ValueError("No timer running")

        # Stop the timer
        if end_time is None:
            end_time = datetime.utcnow()

        duration = self._calculate_duration(running_timer["start_time"], end_time)

        update_doc = {
            "end_time": end_time,
            "duration_minutes": duration,
            "updated_at": datetime.utcnow(),
        }

        updated_doc = await self.time_entries.find_one_and_update(
            {"_id": running_timer["_id"]},
            {"$set": update_doc},
            return_document=True,
        )

        return self._doc_to_entry(updated_doc)

    async def get_current_timer(
        self,
        user_id: str,
    ) -> Optional[TimeEntry]:
        """
        Get the currently running timer, if any.

        Args:
            user_id: User ID

        Returns:
            Current running time entry, or None
        """
        running_timer = await self.time_entries.find_one({
            "user_id": user_id,
            "end_time": None,
        })

        if not running_timer:
            return None

        return self._doc_to_entry(running_timer)

    async def list_entries(
        self,
        user_id: str,
        project_slug: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[TimeEntry]:
        """
        List time entries for a user with optional filtering.

        Args:
            user_id: User ID
            project_slug: Optional project filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of time entries
        """
        # Build query
        query = {
            "user_id": user_id,
        }

        if project_slug:
            query["project_slug"] = project_slug

        if start_date or end_date:
            query["start_time"] = {}
            if start_date:
                query["start_time"]["$gte"] = start_date
            if end_date:
                query["start_time"]["$lte"] = end_date

        # Execute query
        cursor = self.time_entries.find(query).sort("start_time", -1)
        entry_docs = await cursor.to_list(length=None)

        # Convert to TimeEntry objects
        return [self._doc_to_entry(doc) for doc in entry_docs]

    async def create_entry(
        self,
        user_id: str,
        entry_create: TimeEntryCreate,
    ) -> TimeEntry:
        """
        Create a manual time entry.

        Args:
            user_id: User ID
            entry_create: Time entry creation data

        Returns:
            Created time entry

        Raises:
            ValueError: If project doesn't exist
        """
        # Validate project exists
        project = await self.projects.find_one({
            "user_id": user_id,
            "slug": entry_create.project_slug,
            "deleted": False,
        })

        if not project:
            raise ValueError("Project not found")

        # Calculate duration if not provided
        duration = entry_create.duration_minutes
        if duration is None and entry_create.end_time:
            duration = self._calculate_duration(
                entry_create.start_time,
                entry_create.end_time,
            )

        # Create entry
        now = datetime.utcnow()
        entry_doc = {
            "user_id": user_id,
            "project_slug": entry_create.project_slug,
            "description": entry_create.description,
            "start_time": entry_create.start_time,
            "end_time": entry_create.end_time,
            "duration_minutes": duration,
            "created_at": now,
            "updated_at": now,
        }

        result = await self.time_entries.insert_one(entry_doc)
        entry_doc["_id"] = result.inserted_id

        return self._doc_to_entry(entry_doc)

    async def update_entry(
        self,
        user_id: str,
        entry_id: str,
        entry_update: TimeEntryUpdate,
    ) -> TimeEntry:
        """
        Update a time entry.

        Args:
            user_id: User ID
            entry_id: Time entry ID
            entry_update: Update data

        Returns:
            Updated time entry

        Raises:
            ValueError: If entry not found
        """
        # Verify entry exists
        try:
            object_id = ObjectId(entry_id)
        except Exception:
            raise ValueError("Invalid entry ID format")

        existing = await self.time_entries.find_one({
            "_id": object_id,
            "user_id": user_id,
        })

        if not existing:
            raise ValueError("Time entry not found")

        # Build update document
        update_doc = {
            "updated_at": datetime.utcnow(),
        }

        if entry_update.description is not None:
            update_doc["description"] = entry_update.description
        if entry_update.end_time is not None:
            update_doc["end_time"] = entry_update.end_time
        if entry_update.duration_minutes is not None:
            update_doc["duration_minutes"] = entry_update.duration_minutes

        # Update in database
        updated_doc = await self.time_entries.find_one_and_update(
            {"_id": object_id, "user_id": user_id},
            {"$set": update_doc},
            return_document=True,
        )

        return self._doc_to_entry(updated_doc)

    async def delete_entry(
        self,
        user_id: str,
        entry_id: str,
    ) -> dict:
        """
        Delete a time entry.

        Args:
            user_id: User ID
            entry_id: Time entry ID

        Returns:
            Dictionary with deleted_count

        Raises:
            ValueError: If entry not found
        """
        # Verify entry exists
        try:
            object_id = ObjectId(entry_id)
        except Exception:
            raise ValueError("Invalid entry ID format")

        existing = await self.time_entries.find_one({
            "_id": object_id,
            "user_id": user_id,
        })

        if not existing:
            raise ValueError("Time entry not found")

        # Delete (hard delete for time entries)
        result = await self.time_entries.delete_one({
            "_id": object_id,
            "user_id": user_id,
        })

        return {"deleted_count": result.deleted_count}
