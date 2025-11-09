"""Tests for TimerService."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId


@pytest.mark.asyncio
class TestTimerServiceStart:
    """Tests for starting timers."""

    async def test_start_timer_success(self):
        """Test successfully starting a timer."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "time_entries": mock_entries,
            "projects": mock_projects,
        }[key]

        # No running timer
        mock_entries.find_one.return_value = None
        # Project exists
        mock_projects.find_one.return_value = {
            "_id": ObjectId(),
            "slug": "learn-rust",
            "deleted": False,
        }
        mock_entries.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = TimerService(mock_db)
        start_time = datetime.utcnow()

        entry = await service.start_timer(
            user_id="user123",
            project_slug="learn-rust",
            description="Reading chapter 3",
            start_time=start_time,
        )

        assert entry.project_slug == "learn-rust"
        assert entry.description == "Reading chapter 3"
        assert entry.end_time is None
        assert entry.duration_minutes is None

    async def test_start_timer_with_running_timer(self):
        """Test starting timer when one is already running fails."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "time_entries": mock_entries,
            "projects": mock_projects,
        }[key]

        # Running timer exists
        mock_entries.find_one.return_value = {
            "_id": ObjectId(),
            "user_id": "user123",
            "end_time": None,
        }

        service = TimerService(mock_db)

        with pytest.raises(ValueError, match="Timer already running"):
            await service.start_timer(
                user_id="user123",
                project_slug="learn-rust",
                description="Reading",
            )

    async def test_start_timer_with_nonexistent_project(self):
        """Test starting timer with invalid project fails."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "time_entries": mock_entries,
            "projects": mock_projects,
        }[key]

        # No running timer
        mock_entries.find_one.return_value = None
        # Project doesn't exist
        mock_projects.find_one.return_value = None

        service = TimerService(mock_db)

        with pytest.raises(ValueError, match="Project not found"):
            await service.start_timer(
                user_id="user123",
                project_slug="nonexistent",
                description="Reading",
            )


@pytest.mark.asyncio
class TestTimerServiceStop:
    """Tests for stopping timers."""

    async def test_stop_timer_success(self):
        """Test successfully stopping a running timer."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_db.__getitem__.return_value = mock_entries

        start_time = datetime.utcnow() - timedelta(hours=2)
        entry_id = ObjectId()

        # Running timer exists
        running_entry = {
            "_id": entry_id,
            "user_id": "user123",
            "project_slug": "learn-rust",
            "description": "Reading",
            "start_time": start_time,
            "end_time": None,
            "duration_minutes": None,
            "created_at": start_time,
            "updated_at": start_time,
        }
        mock_entries.find_one.return_value = running_entry

        # Updated entry with end_time and duration
        end_time = datetime.utcnow()
        stopped_entry = running_entry.copy()
        stopped_entry["end_time"] = end_time
        stopped_entry["duration_minutes"] = 120  # 2 hours
        mock_entries.find_one_and_update.return_value = stopped_entry

        service = TimerService(mock_db)
        entry = await service.stop_timer(user_id="user123", end_time=end_time)

        assert entry.end_time is not None
        assert entry.duration_minutes == 120

    async def test_stop_timer_no_running_timer(self):
        """Test stopping timer when none is running fails."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_db.__getitem__.return_value = mock_entries

        # No running timer
        mock_entries.find_one.return_value = None

        service = TimerService(mock_db)

        with pytest.raises(ValueError, match="No timer running"):
            await service.stop_timer(user_id="user123")


@pytest.mark.asyncio
class TestTimerServiceGetCurrent:
    """Tests for getting current timer."""

    async def test_get_current_timer_found(self):
        """Test getting current running timer."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_db.__getitem__.return_value = mock_entries

        start_time = datetime.utcnow()
        running_entry = {
            "_id": ObjectId(),
            "user_id": "user123",
            "project_slug": "learn-rust",
            "description": "Reading",
            "start_time": start_time,
            "end_time": None,
            "duration_minutes": None,
            "created_at": start_time,
            "updated_at": start_time,
        }
        mock_entries.find_one.return_value = running_entry

        service = TimerService(mock_db)
        entry = await service.get_current_timer(user_id="user123")

        assert entry is not None
        assert entry.project_slug == "learn-rust"
        assert entry.end_time is None

    async def test_get_current_timer_none(self):
        """Test getting current timer when none is running."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_db.__getitem__.return_value = mock_entries

        mock_entries.find_one.return_value = None

        service = TimerService(mock_db)
        entry = await service.get_current_timer(user_id="user123")

        assert entry is None


@pytest.mark.asyncio
class TestTimerServiceList:
    """Tests for listing time entries."""

    async def test_list_entries_all(self):
        """Test listing all time entries for a user."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = MagicMock()
        mock_db.__getitem__.return_value = mock_entries

        # Mock cursor
        mock_cursor = MagicMock()
        start_time = datetime.utcnow()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": ObjectId(),
                "user_id": "user123",
                "project_slug": "learn-rust",
                "description": "Entry 1",
                "start_time": start_time,
                "end_time": start_time + timedelta(hours=1),
                "duration_minutes": 60,
                "created_at": start_time,
                "updated_at": start_time,
            },
            {
                "_id": ObjectId(),
                "user_id": "user123",
                "project_slug": "learn-python",
                "description": "Entry 2",
                "start_time": start_time,
                "end_time": start_time + timedelta(hours=2),
                "duration_minutes": 120,
                "created_at": start_time,
                "updated_at": start_time,
            },
        ])
        mock_cursor.sort.return_value = mock_cursor
        mock_entries.find.return_value = mock_cursor

        service = TimerService(mock_db)
        entries = await service.list_entries(user_id="user123")

        assert len(entries) == 2
        assert entries[0].project_slug == "learn-rust"
        assert entries[1].project_slug == "learn-python"

    async def test_list_entries_filtered_by_project(self):
        """Test listing entries filtered by project."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = MagicMock()
        mock_db.__getitem__.return_value = mock_entries

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_cursor.sort.return_value = mock_cursor
        mock_entries.find.return_value = mock_cursor

        service = TimerService(mock_db)
        await service.list_entries(user_id="user123", project_slug="learn-rust")

        # Verify find was called with project filter
        call_args = mock_entries.find.call_args[0][0]
        assert call_args["project_slug"] == "learn-rust"

    async def test_list_entries_filtered_by_date_range(self):
        """Test listing entries filtered by date range."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = MagicMock()
        mock_db.__getitem__.return_value = mock_entries

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_cursor.sort.return_value = mock_cursor
        mock_entries.find.return_value = mock_cursor

        service = TimerService(mock_db)
        start_date = datetime(2025, 11, 1)
        end_date = datetime(2025, 11, 30)

        await service.list_entries(
            user_id="user123",
            start_date=start_date,
            end_date=end_date,
        )

        # Verify find was called with date range filter
        call_args = mock_entries.find.call_args[0][0]
        assert "start_time" in call_args
        assert "$gte" in call_args["start_time"]
        assert "$lte" in call_args["start_time"]


@pytest.mark.asyncio
class TestTimerServiceCreate:
    """Tests for creating manual time entries."""

    async def test_create_entry_success(self):
        """Test creating a manual time entry."""
        from app.services.timer_service import TimerService
        from app.models.time_entry import TimeEntryCreate

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "time_entries": mock_entries,
            "projects": mock_projects,
        }[key]

        # Project exists
        mock_projects.find_one.return_value = {
            "_id": ObjectId(),
            "slug": "learn-rust",
            "deleted": False,
        }
        mock_entries.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = TimerService(mock_db)
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()

        entry_data = TimeEntryCreate(
            project_slug="learn-rust",
            description="Reading chapter 3",
            start_time=start_time,
            end_time=end_time,
            duration_minutes=120,
        )

        entry = await service.create_entry(
            user_id="user123",
            entry_create=entry_data,
        )

        assert entry.project_slug == "learn-rust"
        assert entry.duration_minutes == 120

    async def test_create_entry_calculates_duration(self):
        """Test creating entry auto-calculates duration if not provided."""
        from app.services.timer_service import TimerService
        from app.models.time_entry import TimeEntryCreate

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "time_entries": mock_entries,
            "projects": mock_projects,
        }[key]

        # Project exists
        mock_projects.find_one.return_value = {
            "_id": ObjectId(),
            "slug": "learn-rust",
            "deleted": False,
        }
        mock_entries.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = TimerService(mock_db)
        start_time = datetime.utcnow() - timedelta(hours=2)
        end_time = datetime.utcnow()

        entry_data = TimeEntryCreate(
            project_slug="learn-rust",
            description="Reading",
            start_time=start_time,
            end_time=end_time,
            # No duration provided
        )

        entry = await service.create_entry(
            user_id="user123",
            entry_create=entry_data,
        )

        # Duration should be calculated (approximately 120 minutes)
        assert entry.duration_minutes is not None
        assert 119 <= entry.duration_minutes <= 121


@pytest.mark.asyncio
class TestTimerServiceUpdate:
    """Tests for updating time entries."""

    async def test_update_entry_success(self):
        """Test updating a time entry."""
        from app.services.timer_service import TimerService
        from app.models.time_entry import TimeEntryUpdate

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_db.__getitem__.return_value = mock_entries

        entry_id = ObjectId()
        start_time = datetime.utcnow() - timedelta(hours=2)
        existing_entry = {
            "_id": entry_id,
            "user_id": "user123",
            "project_slug": "learn-rust",
            "description": "Old description",
            "start_time": start_time,
            "end_time": None,
            "duration_minutes": None,
            "created_at": start_time,
            "updated_at": start_time,
        }

        mock_entries.find_one.return_value = existing_entry
        updated_entry = existing_entry.copy()
        updated_entry["description"] = "New description"
        mock_entries.find_one_and_update.return_value = updated_entry

        service = TimerService(mock_db)
        update_data = TimeEntryUpdate(description="New description")

        entry = await service.update_entry(
            user_id="user123",
            entry_id=str(entry_id),
            entry_update=update_data,
        )

        assert entry.description == "New description"

    async def test_update_entry_not_found(self):
        """Test updating non-existent entry fails."""
        from app.services.timer_service import TimerService
        from app.models.time_entry import TimeEntryUpdate

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_db.__getitem__.return_value = mock_entries

        mock_entries.find_one.return_value = None

        service = TimerService(mock_db)
        update_data = TimeEntryUpdate(description="New description")

        with pytest.raises(ValueError, match="Time entry not found"):
            await service.update_entry(
                user_id="user123",
                entry_id=str(ObjectId()),
                entry_update=update_data,
            )


@pytest.mark.asyncio
class TestTimerServiceDelete:
    """Tests for deleting time entries."""

    async def test_delete_entry_success(self):
        """Test deleting a time entry."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_db.__getitem__.return_value = mock_entries

        entry_id = ObjectId()
        mock_entries.find_one.return_value = {"_id": entry_id, "user_id": "user123"}
        mock_entries.delete_one.return_value = AsyncMock(deleted_count=1)

        service = TimerService(mock_db)
        result = await service.delete_entry(
            user_id="user123",
            entry_id=str(entry_id),
        )

        assert result["deleted_count"] == 1

    async def test_delete_entry_not_found(self):
        """Test deleting non-existent entry fails."""
        from app.services.timer_service import TimerService

        mock_db = MagicMock()
        mock_entries = AsyncMock()
        mock_db.__getitem__.return_value = mock_entries

        mock_entries.find_one.return_value = None

        service = TimerService(mock_db)

        with pytest.raises(ValueError, match="Time entry not found"):
            await service.delete_entry(
                user_id="user123",
                entry_id=str(ObjectId()),
            )
