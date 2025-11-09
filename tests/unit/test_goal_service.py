"""Tests for GoalService."""
import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId


@pytest.mark.asyncio
class TestGoalServiceCreate:
    """Tests for creating goals."""

    async def test_create_goal_success(self):
        """Test successful goal creation."""
        from app.services.goal_service import GoalService
        from app.models.goal import GoalCreate

        mock_db = MagicMock()
        mock_goals = AsyncMock()
        mock_db.__getitem__.return_value = mock_goals

        # No existing goals with same slug
        mock_goals.find_one.return_value = None
        mock_goals.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = GoalService(mock_db)
        goal_data = GoalCreate(
            title="Become a Great Leader",
            area="Leadership",
            content="Focus on developing leadership skills",
        )

        goal = await service.create_goal(
            user_id="user123",
            goal_create=goal_data,
        )

        assert goal.title == "Become a Great Leader"
        assert goal.area == "Leadership"
        assert goal.slug == "become-a-great-leader"
        assert goal.folder == "active"
        assert goal.deleted is False

    async def test_create_goal_duplicate_slug(self):
        """Test creating goal with duplicate slug generates unique slug."""
        from app.services.goal_service import GoalService
        from app.models.goal import GoalCreate

        mock_db = MagicMock()
        mock_goals = AsyncMock()
        mock_db.__getitem__.return_value = mock_goals

        # First call: existing goal found
        # Second call: no conflict for new slug
        mock_goals.find_one.side_effect = [
            {"_id": ObjectId(), "slug": "become-a-great-leader"},  # Conflict
            None,  # No conflict with -2
        ]
        mock_goals.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = GoalService(mock_db)
        goal_data = GoalCreate(
            title="Become a Great Leader",
            area="Leadership",
        )

        goal = await service.create_goal(
            user_id="user123",
            goal_create=goal_data,
        )

        assert goal.slug == "become-a-great-leader-2"


@pytest.mark.asyncio
class TestGoalServiceList:
    """Tests for listing goals."""

    async def test_list_goals_all(self):
        """Test listing all goals for a user."""
        from app.services.goal_service import GoalService

        mock_db = MagicMock()
        mock_goals = MagicMock()
        mock_db.__getitem__.return_value = mock_goals

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": ObjectId(),
                "user_id": "user123",
                "title": "Goal 1",
                "area": "Leadership",
                "slug": "goal-1",
                "content": "",
                "created": datetime.now(),
                "last_reviewed": None,
                "folder": "active",
                "deleted": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "_id": ObjectId(),
                "user_id": "user123",
                "title": "Goal 2",
                "area": "Health",
                "slug": "goal-2",
                "content": "",
                "created": datetime.now(),
                "last_reviewed": None,
                "folder": "active",
                "deleted": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        ])
        mock_goals.find.return_value = mock_cursor

        service = GoalService(mock_db)
        goals = await service.list_goals(user_id="user123")

        assert len(goals) == 2
        assert goals[0].title == "Goal 1"
        assert goals[1].title == "Goal 2"

    async def test_list_goals_filtered_by_folder(self):
        """Test listing goals filtered by folder."""
        from app.services.goal_service import GoalService

        mock_db = MagicMock()
        mock_goals = MagicMock()
        mock_db.__getitem__.return_value = mock_goals

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_goals.find.return_value = mock_cursor

        service = GoalService(mock_db)
        await service.list_goals(user_id="user123", folder="incubator")

        # Verify find was called with folder filter
        call_args = mock_goals.find.call_args[0][0]
        assert call_args["folder"] == "incubator"
        assert call_args["deleted"] is False

    async def test_list_goals_filtered_by_area(self):
        """Test listing goals filtered by area."""
        from app.services.goal_service import GoalService

        mock_db = MagicMock()
        mock_goals = MagicMock()
        mock_db.__getitem__.return_value = mock_goals

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_goals.find.return_value = mock_cursor

        service = GoalService(mock_db)
        await service.list_goals(user_id="user123", area="Leadership")

        # Verify find was called with area filter
        call_args = mock_goals.find.call_args[0][0]
        assert call_args["area"] == "Leadership"

    async def test_list_goals_excludes_deleted(self):
        """Test that deleted goals are excluded."""
        from app.services.goal_service import GoalService

        mock_db = MagicMock()
        mock_goals = MagicMock()
        mock_db.__getitem__.return_value = mock_goals

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_goals.find.return_value = mock_cursor

        service = GoalService(mock_db)
        await service.list_goals(user_id="user123")

        # Verify deleted: False is in query
        call_args = mock_goals.find.call_args[0][0]
        assert call_args["deleted"] is False


@pytest.mark.asyncio
class TestGoalServiceGet:
    """Tests for getting a single goal."""

    async def test_get_goal_by_slug_found(self):
        """Test getting goal by slug when it exists."""
        from app.services.goal_service import GoalService

        mock_db = MagicMock()
        mock_goals = AsyncMock()
        mock_db.__getitem__.return_value = mock_goals

        mock_goals.find_one.return_value = {
            "_id": ObjectId(),
            "user_id": "user123",
            "title": "Test Goal",
            "area": "Leadership",
            "slug": "test-goal",
            "content": "Content here",
            "created": datetime.now(),
            "last_reviewed": None,
            "folder": "active",
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        service = GoalService(mock_db)
        goal = await service.get_goal_by_slug(
            user_id="user123",
            slug="test-goal",
        )

        assert goal.title == "Test Goal"
        assert goal.slug == "test-goal"

    async def test_get_goal_by_slug_not_found(self):
        """Test getting goal by slug when it doesn't exist."""
        from app.services.goal_service import GoalService

        mock_db = MagicMock()
        mock_goals = AsyncMock()
        mock_db.__getitem__.return_value = mock_goals

        mock_goals.find_one.return_value = None

        service = GoalService(mock_db)

        with pytest.raises(ValueError, match="Goal not found"):
            await service.get_goal_by_slug(
                user_id="user123",
                slug="nonexistent",
            )


@pytest.mark.asyncio
class TestGoalServiceUpdate:
    """Tests for updating goals."""

    async def test_update_goal_content(self):
        """Test updating goal content."""
        from app.services.goal_service import GoalService
        from app.models.goal import GoalUpdate

        mock_db = MagicMock()
        mock_goals = AsyncMock()
        mock_db.__getitem__.return_value = mock_goals

        existing_goal = {
            "_id": ObjectId(),
            "user_id": "user123",
            "title": "Test Goal",
            "area": "Leadership",
            "slug": "test-goal",
            "content": "Old content",
            "created": datetime.now(),
            "folder": "active",
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # find_one returns existing, find_one_and_update returns updated
        mock_goals.find_one.return_value = existing_goal
        updated_goal = existing_goal.copy()
        updated_goal["content"] = "New content"
        mock_goals.find_one_and_update.return_value = updated_goal

        service = GoalService(mock_db)
        update_data = GoalUpdate(content="New content")

        goal = await service.update_goal(
            user_id="user123",
            slug="test-goal",
            goal_update=update_data,
        )

        assert goal.content == "New content"

    async def test_update_goal_title_changes_slug(self):
        """Test that updating title generates new slug."""
        from app.services.goal_service import GoalService
        from app.models.goal import GoalUpdate

        mock_db = MagicMock()
        mock_goals = AsyncMock()
        mock_db.__getitem__.return_value = mock_goals

        existing_goal = {
            "_id": ObjectId(),
            "user_id": "user123",
            "title": "Old Title",
            "area": "Leadership",
            "slug": "old-title",
            "content": "",
            "created": datetime.now(),
            "folder": "active",
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # First find_one: get existing goal
        # Second find_one: check new slug availability
        mock_goals.find_one.side_effect = [
            existing_goal,
            None,  # New slug available
        ]
        updated_goal = existing_goal.copy()
        updated_goal["title"] = "New Title"
        updated_goal["slug"] = "new-title"
        mock_goals.find_one_and_update.return_value = updated_goal

        service = GoalService(mock_db)
        update_data = GoalUpdate(title="New Title")

        goal = await service.update_goal(
            user_id="user123",
            slug="old-title",
            goal_update=update_data,
        )

        assert goal.title == "New Title"
        assert goal.slug == "new-title"


@pytest.mark.asyncio
class TestGoalServiceDelete:
    """Tests for soft-deleting goals."""

    async def test_delete_goal_success(self):
        """Test soft-deleting a goal."""
        from app.services.goal_service import GoalService

        mock_db = MagicMock()
        mock_goals = AsyncMock()
        mock_db.__getitem__.return_value = mock_goals

        existing_goal = {
            "_id": ObjectId(),
            "user_id": "user123",
            "deleted": False,
        }

        mock_goals.find_one.return_value = existing_goal
        mock_goals.update_one.return_value = AsyncMock(modified_count=1)

        service = GoalService(mock_db)
        result = await service.delete_goal(
            user_id="user123",
            slug="test-goal",
        )

        assert result["deleted_count"] == 1

    async def test_delete_goal_not_found(self):
        """Test deleting non-existent goal fails."""
        from app.services.goal_service import GoalService

        mock_db = MagicMock()
        mock_goals = AsyncMock()
        mock_db.__getitem__.return_value = mock_goals

        mock_goals.find_one.return_value = None

        service = GoalService(mock_db)

        with pytest.raises(ValueError, match="Goal not found"):
            await service.delete_goal(
                user_id="user123",
                slug="nonexistent",
            )
