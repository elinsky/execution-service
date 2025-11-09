"""Tests for Pydantic models."""
import pytest
from datetime import date, datetime
from pydantic import ValidationError


class TestProjectModel:
    """Tests for Project model."""

    def test_project_model_imports(self):
        """Test that project models can be imported."""
        from app.models.project import (
            ProjectFolder,
            ProjectType,
            ProjectBase,
            ProjectCreate,
            ProjectUpdate,
            Project,
        )
        assert ProjectFolder is not None
        assert ProjectType is not None
        assert ProjectBase is not None
        assert ProjectCreate is not None
        assert ProjectUpdate is not None
        assert Project is not None

    def test_project_folder_enum_values(self):
        """Test ProjectFolder enum has correct values."""
        from app.models.project import ProjectFolder

        assert ProjectFolder.ACTIVE.value == "active"
        assert ProjectFolder.INCUBATOR.value == "incubator"
        assert ProjectFolder.COMPLETED.value == "completed"
        assert ProjectFolder.DESCOPED.value == "descoped"

    def test_project_type_enum_values(self):
        """Test ProjectType enum has correct values."""
        from app.models.project import ProjectType

        assert ProjectType.STANDARD.value == "standard"
        assert ProjectType.COORDINATION.value == "coordination"
        assert ProjectType.HABIT.value == "habit"
        assert ProjectType.GOAL.value == "goal"

    def test_project_create_minimal(self):
        """Test creating a project with minimal required fields."""
        from app.models.project import ProjectCreate

        project = ProjectCreate(
            title="Learn Rust",
            area="engineering",
        )

        assert project.title == "Learn Rust"
        assert project.area == "engineering"
        assert project.folder.value == "active"  # default
        assert project.type.value == "standard"  # default
        assert project.due is None
        assert project.content == ""

    def test_project_create_full(self):
        """Test creating a project with all fields."""
        from app.models.project import ProjectCreate, ProjectFolder, ProjectType

        due_date = date(2025, 12, 31)
        project = ProjectCreate(
            title="DE Shaw TPM Role",
            area="career",
            folder=ProjectFolder.ACTIVE,
            type=ProjectType.STANDARD,
            due=due_date,
            content="## Next Steps\n- Apply to position",
        )

        assert project.title == "DE Shaw TPM Role"
        assert project.area == "career"
        assert project.folder == ProjectFolder.ACTIVE
        assert project.type == ProjectType.STANDARD
        assert project.due == due_date
        assert project.content == "## Next Steps\n- Apply to position"

    def test_project_create_missing_required_fields(self):
        """Test that creating a project without required fields fails."""
        from app.models.project import ProjectCreate

        with pytest.raises(ValidationError) as exc_info:
            ProjectCreate()

        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "title" in field_names
        assert "area" in field_names

    def test_project_update_partial(self):
        """Test ProjectUpdate allows partial updates."""
        from app.models.project import ProjectUpdate, ProjectFolder

        # Can update just title
        update = ProjectUpdate(title="Updated Title")
        assert update.title == "Updated Title"
        assert update.area is None
        assert update.folder is None

        # Can update just folder
        update = ProjectUpdate(folder=ProjectFolder.COMPLETED)
        assert update.folder == ProjectFolder.COMPLETED
        assert update.title is None

    def test_project_full_model(self):
        """Test full Project model with all fields."""
        from app.models.project import Project, ProjectFolder, ProjectType

        now = datetime.now()
        today = date.today()

        project = Project(
            _id="507f1f77bcf86cd799439011",
            user_id="user123",
            slug="learn-rust",
            title="Learn Rust",
            area="engineering",
            folder=ProjectFolder.ACTIVE,
            type=ProjectType.STANDARD,
            due=date(2025, 12, 31),
            content="## Goals\n- Complete Rust book",
            created=today,
            started=today,
            last_reviewed=today,
            completed=None,
            descoped=None,
            deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )

        assert project.id == "507f1f77bcf86cd799439011"
        assert project.user_id == "user123"
        assert project.slug == "learn-rust"
        assert project.title == "Learn Rust"
        assert project.deleted is False

    def test_project_model_alias_id_field(self):
        """Test that _id field is aliased to id."""
        from app.models.project import Project, ProjectFolder, ProjectType

        now = datetime.now()
        today = date.today()

        # Can create with _id
        project = Project(
            _id="abc123",
            user_id="user123",
            slug="test",
            title="Test",
            area="test",
            folder=ProjectFolder.ACTIVE,
            type=ProjectType.STANDARD,
            content="",
            created=today,
            deleted=False,
            created_at=now,
            updated_at=now,
        )

        # Access via id property
        assert project.id == "abc123"


class TestUserModel:
    """Tests for User model."""

    def test_user_model_imports(self):
        """Test that user models can be imported."""
        from app.models.user import UserBase, UserCreate, User, UserInDB

        assert UserBase is not None
        assert UserCreate is not None
        assert User is not None
        assert UserInDB is not None

    def test_user_create_valid(self):
        """Test creating a valid user."""
        from app.models.user import UserCreate

        user = UserCreate(
            email="brian@example.com",
            password="securepassword123",
            name="Brian",
        )

        assert user.email == "brian@example.com"
        assert user.password == "securepassword123"
        assert user.name == "Brian"

    def test_user_create_missing_required(self):
        """Test user creation fails without required fields."""
        from app.models.user import UserCreate

        with pytest.raises(ValidationError) as exc_info:
            UserCreate()

        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "email" in field_names
        assert "password" in field_names
        assert "name" in field_names

    def test_user_in_db_has_hashed_password(self):
        """Test UserInDB model has hashed_password field."""
        from app.models.user import UserInDB

        now = datetime.now()
        user = UserInDB(
            _id="user123",
            email="brian@example.com",
            hashed_password="$2b$12$hashed...",
            name="Brian",
            created_at=now,
            updated_at=now,
        )

        assert user.id == "user123"
        assert user.hashed_password == "$2b$12$hashed..."
        assert user.email == "brian@example.com"


class TestActionModel:
    """Tests for Action model."""

    def test_action_model_imports(self):
        """Test that action models can be imported."""
        from app.models.action import ActionState, ActionBase, ActionCreate, Action

        assert ActionState is not None
        assert ActionBase is not None
        assert ActionCreate is not None
        assert Action is not None

    def test_action_state_enum_values(self):
        """Test ActionState enum has correct values."""
        from app.models.action import ActionState

        assert ActionState.NEXT.value == "next"
        assert ActionState.WAITING.value == "waiting"
        assert ActionState.DEFERRED.value == "deferred"
        assert ActionState.INCUBATING.value == "incubating"
        assert ActionState.COMPLETED.value == "completed"

    def test_action_create_minimal(self):
        """Test creating an action with minimal fields."""
        from app.models.action import ActionCreate

        action = ActionCreate(
            text="Review pull request",
            context="@macbook",
        )

        assert action.text == "Review pull request"
        assert action.context == "@macbook"
        assert action.project_slug is None
        assert action.due is None
        assert action.defer is None

    def test_action_create_with_project(self):
        """Test creating an action linked to a project."""
        from app.models.action import ActionCreate

        action = ActionCreate(
            text="Write unit tests",
            context="@macbook",
            project_slug="execution-service",
        )

        assert action.text == "Write unit tests"
        assert action.context == "@macbook"
        assert action.project_slug == "execution-service"

    def test_action_create_with_dates(self):
        """Test creating an action with due and defer dates."""
        from app.models.action import ActionCreate

        due_date = date(2025, 11, 15)
        defer_date = date(2025, 11, 10)

        action = ActionCreate(
            text="Submit tax documents",
            context="@home",
            due=due_date,
            defer=defer_date,
        )

        assert action.due == due_date
        assert action.defer == defer_date


class TestTimeEntryModel:
    """Tests for TimeEntry model."""

    def test_time_entry_model_imports(self):
        """Test that time entry models can be imported."""
        from app.models.time_entry import TimeEntryBase, TimeEntryCreate, TimeEntry

        assert TimeEntryBase is not None
        assert TimeEntryCreate is not None
        assert TimeEntry is not None

    def test_time_entry_create_valid(self):
        """Test creating a valid time entry."""
        from app.models.time_entry import TimeEntryCreate

        start_time = datetime(2025, 11, 9, 14, 30)

        entry = TimeEntryCreate(
            project_slug="learn-rust",
            description="Reading chapter 5",
            start_time=start_time,
        )

        assert entry.project_slug == "learn-rust"
        assert entry.description == "Reading chapter 5"
        assert entry.start_time == start_time
        assert entry.end_time is None
        assert entry.duration_minutes is None

    def test_time_entry_with_end_time(self):
        """Test time entry with end time."""
        from app.models.time_entry import TimeEntryCreate

        start_time = datetime(2025, 11, 9, 14, 30)
        end_time = datetime(2025, 11, 9, 15, 45)

        entry = TimeEntryCreate(
            project_slug="learn-rust",
            description="Reading chapter 5",
            start_time=start_time,
            end_time=end_time,
        )

        assert entry.start_time == start_time
        assert entry.end_time == end_time


class TestGoalModel:
    """Tests for Goal model."""

    def test_goal_model_imports(self):
        """Test that goal models can be imported."""
        from app.models.goal import GoalBase, GoalCreate, GoalUpdate, Goal

        assert GoalBase is not None
        assert GoalCreate is not None
        assert GoalUpdate is not None
        assert Goal is not None

    def test_goal_create_minimal(self):
        """Test creating a goal with minimal fields."""
        from app.models.goal import GoalCreate

        goal = GoalCreate(
            title="Become a Staff Engineer",
            area="career",
        )

        assert goal.title == "Become a Staff Engineer"
        assert goal.area == "career"
        assert goal.content == ""
