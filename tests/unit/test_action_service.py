"""Tests for ActionService."""
import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from bson import ObjectId


@pytest.mark.asyncio
class TestActionServiceCreate:
    """Tests for creating actions."""

    async def test_create_action_success(self):
        """Test successful action creation."""
        from app.services.action_service import ActionService
        from app.models.action import ActionCreate

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "actions": mock_actions,
            "projects": mock_projects,
        }[key]

        # No project validation needed (no project_slug)
        mock_actions.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = ActionService(mock_db)
        action_data = ActionCreate(
            text="Review pull request",
            context="@macbook",
        )

        action = await service.create_action(
            user_id="user123",
            action_create=action_data,
        )

        assert action.text == "Review pull request"
        assert action.context == "@macbook"
        assert action.project_slug is None
        assert action.state == "next"
        assert action.deleted is False

    async def test_create_action_with_project(self):
        """Test creating action with project reference."""
        from app.services.action_service import ActionService
        from app.models.action import ActionCreate

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "actions": mock_actions,
            "projects": mock_projects,
        }[key]

        # Project exists
        mock_projects.find_one.return_value = {
            "_id": ObjectId(),
            "slug": "learn-rust",
            "user_id": "user123",
            "deleted": False,
        }
        mock_actions.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = ActionService(mock_db)
        action_data = ActionCreate(
            text="Read chapter 3",
            context="@home",
            project_slug="learn-rust",
        )

        action = await service.create_action(
            user_id="user123",
            action_create=action_data,
        )

        assert action.text == "Read chapter 3"
        assert action.project_slug == "learn-rust"

    async def test_create_action_with_nonexistent_project(self):
        """Test creating action with invalid project fails."""
        from app.services.action_service import ActionService
        from app.models.action import ActionCreate

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "actions": mock_actions,
            "projects": mock_projects,
        }[key]

        # Project does not exist
        mock_projects.find_one.return_value = None

        service = ActionService(mock_db)
        action_data = ActionCreate(
            text="Read chapter 3",
            context="@home",
            project_slug="nonexistent",
        )

        with pytest.raises(ValueError, match="Project not found"):
            await service.create_action(
                user_id="user123",
                action_create=action_data,
            )

    async def test_create_action_with_dates(self):
        """Test creating action with due and defer dates."""
        from app.services.action_service import ActionService
        from app.models.action import ActionCreate

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "actions": mock_actions,
            "projects": mock_projects,
        }[key]

        mock_actions.insert_one.return_value = AsyncMock(inserted_id=ObjectId())

        service = ActionService(mock_db)
        due_date = date(2025, 12, 31)
        defer_date = date(2025, 12, 1)
        action_data = ActionCreate(
            text="Submit report",
            context="@macbook",
            due=due_date,
            defer=defer_date,
        )

        action = await service.create_action(
            user_id="user123",
            action_create=action_data,
        )

        assert action.due == due_date
        assert action.defer == defer_date


@pytest.mark.asyncio
class TestActionServiceList:
    """Tests for listing actions."""

    async def test_list_actions_all(self):
        """Test listing all actions for a user."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = MagicMock()
        mock_db.__getitem__.return_value = mock_actions

        # Mock cursor
        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": ObjectId(),
                "user_id": "user123",
                "text": "Action 1",
                "context": "@macbook",
                "project_slug": None,
                "state": "next",
                "action_date": date.today(),
                "deleted": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
            {
                "_id": ObjectId(),
                "user_id": "user123",
                "text": "Action 2",
                "context": "@home",
                "project_slug": "learn-rust",
                "state": "next",
                "action_date": date.today(),
                "deleted": False,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        ])
        mock_actions.find.return_value = mock_cursor

        service = ActionService(mock_db)
        actions = await service.list_actions(user_id="user123")

        assert len(actions) == 2
        assert actions[0].text == "Action 1"
        assert actions[1].text == "Action 2"

    async def test_list_actions_filtered_by_context(self):
        """Test listing actions filtered by context."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = MagicMock()
        mock_db.__getitem__.return_value = mock_actions

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_actions.find.return_value = mock_cursor

        service = ActionService(mock_db)
        await service.list_actions(user_id="user123", context="@macbook")

        # Verify find was called with context filter
        call_args = mock_actions.find.call_args[0][0]
        assert call_args["context"] == "@macbook"
        assert call_args["deleted"] is False

    async def test_list_actions_filtered_by_project(self):
        """Test listing actions filtered by project."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = MagicMock()
        mock_db.__getitem__.return_value = mock_actions

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_actions.find.return_value = mock_cursor

        service = ActionService(mock_db)
        await service.list_actions(user_id="user123", project_slug="learn-rust")

        # Verify find was called with project filter
        call_args = mock_actions.find.call_args[0][0]
        assert call_args["project_slug"] == "learn-rust"

    async def test_list_actions_filtered_by_state(self):
        """Test listing actions filtered by state."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = MagicMock()
        mock_db.__getitem__.return_value = mock_actions

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_actions.find.return_value = mock_cursor

        service = ActionService(mock_db)
        await service.list_actions(user_id="user123", state="completed")

        # Verify find was called with state filter
        call_args = mock_actions.find.call_args[0][0]
        assert call_args["state"] == "completed"

    async def test_list_actions_excludes_deleted(self):
        """Test that deleted actions are excluded."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = MagicMock()
        mock_db.__getitem__.return_value = mock_actions

        mock_cursor = MagicMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_actions.find.return_value = mock_cursor

        service = ActionService(mock_db)
        await service.list_actions(user_id="user123")

        # Verify deleted: False is in query
        call_args = mock_actions.find.call_args[0][0]
        assert call_args["deleted"] is False


@pytest.mark.asyncio
class TestActionServiceGet:
    """Tests for getting a single action."""

    async def test_get_action_by_id_found(self):
        """Test getting action by ID when it exists."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_db.__getitem__.return_value = mock_actions

        action_id = ObjectId()
        mock_actions.find_one.return_value = {
            "_id": action_id,
            "user_id": "user123",
            "text": "Test action",
            "context": "@macbook",
            "project_slug": None,
            "state": "next",
            "action_date": date.today(),
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        service = ActionService(mock_db)
        action = await service.get_action_by_id(
            user_id="user123",
            action_id=str(action_id),
        )

        assert action.text == "Test action"
        assert action.id == str(action_id)

    async def test_get_action_by_id_not_found(self):
        """Test getting action by ID when it doesn't exist."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_db.__getitem__.return_value = mock_actions

        mock_actions.find_one.return_value = None

        service = ActionService(mock_db)

        with pytest.raises(ValueError, match="Action not found"):
            await service.get_action_by_id(
                user_id="user123",
                action_id=str(ObjectId()),
            )


@pytest.mark.asyncio
class TestActionServiceUpdate:
    """Tests for updating actions."""

    async def test_update_action_text(self):
        """Test updating action text."""
        from app.services.action_service import ActionService
        from app.models.action import ActionUpdate

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "actions": mock_actions,
            "projects": mock_projects,
        }[key]

        action_id = ObjectId()
        existing_action = {
            "_id": action_id,
            "user_id": "user123",
            "text": "Old text",
            "context": "@macbook",
            "project_slug": None,
            "state": "next",
            "action_date": date.today(),
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # find_one returns existing, find_one_and_update returns updated
        mock_actions.find_one.return_value = existing_action
        updated_action = existing_action.copy()
        updated_action["text"] = "New text"
        mock_actions.find_one_and_update.return_value = updated_action

        service = ActionService(mock_db)
        update_data = ActionUpdate(text="New text")

        action = await service.update_action(
            user_id="user123",
            action_id=str(action_id),
            action_update=update_data,
        )

        assert action.text == "New text"

    async def test_update_action_with_new_project(self):
        """Test updating action to add project reference."""
        from app.services.action_service import ActionService
        from app.models.action import ActionUpdate

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "actions": mock_actions,
            "projects": mock_projects,
        }[key]

        action_id = ObjectId()
        existing_action = {
            "_id": action_id,
            "user_id": "user123",
            "text": "Some action",
            "context": "@macbook",
            "project_slug": None,
            "state": "next",
            "action_date": date.today(),
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        # Project exists
        mock_projects.find_one.return_value = {
            "_id": ObjectId(),
            "slug": "learn-rust",
            "deleted": False,
        }

        mock_actions.find_one.return_value = existing_action
        updated_action = existing_action.copy()
        updated_action["project_slug"] = "learn-rust"
        mock_actions.find_one_and_update.return_value = updated_action

        service = ActionService(mock_db)
        update_data = ActionUpdate(project_slug="learn-rust")

        action = await service.update_action(
            user_id="user123",
            action_id=str(action_id),
            action_update=update_data,
        )

        assert action.project_slug == "learn-rust"

    async def test_update_action_with_invalid_project(self):
        """Test updating action with invalid project fails."""
        from app.services.action_service import ActionService
        from app.models.action import ActionUpdate

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_projects = AsyncMock()
        mock_db.__getitem__.side_effect = lambda key: {
            "actions": mock_actions,
            "projects": mock_projects,
        }[key]

        action_id = ObjectId()
        existing_action = {
            "_id": action_id,
            "user_id": "user123",
            "deleted": False,
        }

        mock_actions.find_one.return_value = existing_action
        # Project does not exist
        mock_projects.find_one.return_value = None

        service = ActionService(mock_db)
        update_data = ActionUpdate(project_slug="nonexistent")

        with pytest.raises(ValueError, match="Project not found"):
            await service.update_action(
                user_id="user123",
                action_id=str(action_id),
                action_update=update_data,
            )


@pytest.mark.asyncio
class TestActionServiceComplete:
    """Tests for completing actions."""

    async def test_complete_action_success(self):
        """Test completing an action."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_db.__getitem__.return_value = mock_actions

        action_id = ObjectId()
        existing_action = {
            "_id": action_id,
            "user_id": "user123",
            "text": "Test action",
            "context": "@macbook",
            "state": "next",
            "action_date": date.today(),
            "deleted": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mock_actions.find_one.return_value = existing_action
        completed_action = existing_action.copy()
        completed_action["state"] = "completed"
        completed_action["completed"] = date.today()
        mock_actions.find_one_and_update.return_value = completed_action

        service = ActionService(mock_db)
        action = await service.complete_action(
            user_id="user123",
            action_id=str(action_id),
        )

        assert action.state == "completed"
        assert action.completed is not None

    async def test_complete_action_not_found(self):
        """Test completing non-existent action fails."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_db.__getitem__.return_value = mock_actions

        mock_actions.find_one.return_value = None

        service = ActionService(mock_db)

        with pytest.raises(ValueError, match="Action not found"):
            await service.complete_action(
                user_id="user123",
                action_id=str(ObjectId()),
            )


@pytest.mark.asyncio
class TestActionServiceDelete:
    """Tests for soft-deleting actions."""

    async def test_delete_action_success(self):
        """Test soft-deleting an action."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_db.__getitem__.return_value = mock_actions

        existing_action = {
            "_id": ObjectId(),
            "user_id": "user123",
            "deleted": False,
        }

        mock_actions.find_one.return_value = existing_action
        mock_actions.update_one.return_value = AsyncMock(modified_count=1)

        service = ActionService(mock_db)
        result = await service.delete_action(
            user_id="user123",
            action_id=str(existing_action["_id"]),
        )

        assert result["deleted_count"] == 1

    async def test_delete_action_not_found(self):
        """Test deleting non-existent action fails."""
        from app.services.action_service import ActionService

        mock_db = MagicMock()
        mock_actions = AsyncMock()
        mock_db.__getitem__.return_value = mock_actions

        mock_actions.find_one.return_value = None

        service = ActionService(mock_db)

        with pytest.raises(ValueError, match="Action not found"):
            await service.delete_action(
                user_id="user123",
                action_id=str(ObjectId()),
            )
