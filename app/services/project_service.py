"""Project service - business logic for project management."""
from datetime import date, datetime
from typing import Optional
from bson import ObjectId

from app.models.project import Project, ProjectCreate, ProjectUpdate, ProjectFolder, ProjectType
from app.utils.slug import slugify, generate_unique_slug


class ProjectService:
    """Service for handling project operations."""

    def __init__(self, db):
        """Initialize service with database connection."""
        self.db = db
        self.projects = db["projects"]

    def _doc_to_project(self, doc: dict) -> Project:
        """
        Convert database document to Project model.

        Handles datetime to date conversion for date fields.
        """
        return Project(
            _id=str(doc["_id"]),
            user_id=doc["user_id"],
            title=doc["title"],
            slug=doc["slug"],
            area=doc["area"],
            folder=doc["folder"],
            type=doc["type"],
            content=doc.get("content", ""),
            created=doc["created"].date() if isinstance(doc["created"], datetime) else doc["created"],
            deleted=doc["deleted"],
            due=doc["due"].date() if doc.get("due") and isinstance(doc["due"], datetime) else doc.get("due"),
            started=doc["started"].date() if doc.get("started") and isinstance(doc["started"], datetime) else doc.get("started"),
            completed=doc["completed"].date() if doc.get("completed") and isinstance(doc["completed"], datetime) else doc.get("completed"),
            last_reviewed=doc["last_reviewed"].date() if doc.get("last_reviewed") and isinstance(doc["last_reviewed"], datetime) else doc.get("last_reviewed"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )

    async def create_project(
        self,
        user_id: str,
        project_create: ProjectCreate,
    ) -> Project:
        """
        Create a new project.

        Args:
            user_id: User ID who owns the project
            project_create: Project creation data

        Returns:
            Created project object

        Raises:
            ValueError: If project creation fails
        """
        # Generate unique slug
        base_slug = slugify(project_create.title)
        slug = await generate_unique_slug(
            self.projects,
            base_slug,
            user_id=user_id,
        )

        # Prepare project document
        now = datetime.utcnow()
        today = date.today()

        project_doc = {
            "user_id": user_id,
            "title": project_create.title,
            "slug": slug,
            "area": project_create.area,
            "folder": project_create.folder.value if project_create.folder else ProjectFolder.ACTIVE.value,
            "type": project_create.type.value if project_create.type else ProjectType.STANDARD.value,
            "content": project_create.content if project_create.content else "",
            "created": datetime.combine(today, datetime.min.time()),
            "deleted": False,
            "created_at": now,
            "updated_at": now,
        }

        # Add optional fields (convert dates to datetime)
        if project_create.due:
            project_doc["due"] = datetime.combine(project_create.due, datetime.min.time())

        # Insert into database
        result = await self.projects.insert_one(project_doc)

        # Add _id to doc for conversion
        project_doc["_id"] = result.inserted_id

        # Return Project object using helper
        return self._doc_to_project(project_doc)

    async def list_projects(
        self,
        user_id: str,
        folder: Optional[str] = None,
        area: Optional[str] = None,
    ) -> list[Project]:
        """
        List projects for a user with optional filtering.

        Args:
            user_id: User ID
            folder: Optional folder filter
            area: Optional area filter

        Returns:
            List of projects
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
        cursor = self.projects.find(query)
        project_docs = await cursor.to_list(length=None)

        # Convert to Project objects using helper
        return [self._doc_to_project(doc) for doc in project_docs]

    async def get_project_by_slug(
        self,
        user_id: str,
        slug: str,
    ) -> Project:
        """
        Get a project by slug.

        Args:
            user_id: User ID
            slug: Project slug

        Returns:
            Project object

        Raises:
            ValueError: If project not found
        """
        project_doc = await self.projects.find_one({
            "user_id": user_id,
            "slug": slug,
            "deleted": False,
        })

        if not project_doc:
            raise ValueError("Project not found")

        return self._doc_to_project(project_doc)

    async def update_project(
        self,
        user_id: str,
        slug: str,
        project_update: ProjectUpdate,
    ) -> Project:
        """
        Update a project.

        Args:
            user_id: User ID
            slug: Project slug
            project_update: Update data

        Returns:
            Updated project object

        Raises:
            ValueError: If project not found
        """
        # First, verify project exists
        existing = await self.projects.find_one({
            "user_id": user_id,
            "slug": slug,
            "deleted": False,
        })

        if not existing:
            raise ValueError("Project not found")

        # Build update document
        update_doc = {
            "updated_at": datetime.utcnow(),
        }

        # Handle title change (regenerate slug)
        if project_update.title is not None:
            base_slug = slugify(project_update.title)
            new_slug = await generate_unique_slug(
                self.projects,
                base_slug,
                user_id=user_id,
                exclude_id=existing["_id"],
            )
            update_doc["title"] = project_update.title
            update_doc["slug"] = new_slug

        # Add other fields if provided
        if project_update.area is not None:
            update_doc["area"] = project_update.area
        if project_update.folder is not None:
            update_doc["folder"] = project_update.folder.value
        if project_update.type is not None:
            update_doc["type"] = project_update.type.value
        if project_update.content is not None:
            update_doc["content"] = project_update.content
        if project_update.due is not None:
            update_doc["due"] = datetime.combine(project_update.due, datetime.min.time())

        # Update in database
        updated_doc = await self.projects.find_one_and_update(
            {"user_id": user_id, "slug": slug, "deleted": False},
            {"$set": update_doc},
            return_document=True,
        )

        return self._doc_to_project(updated_doc)

    async def delete_project(
        self,
        user_id: str,
        slug: str,
    ) -> dict:
        """
        Soft delete a project.

        Args:
            user_id: User ID
            slug: Project slug

        Returns:
            Dictionary with deleted_count

        Raises:
            ValueError: If project not found
        """
        # Verify project exists
        existing = await self.projects.find_one({
            "user_id": user_id,
            "slug": slug,
            "deleted": False,
        })

        if not existing:
            raise ValueError("Project not found")

        # Soft delete
        result = await self.projects.update_one(
            {"user_id": user_id, "slug": slug},
            {"$set": {"deleted": True, "updated_at": datetime.utcnow()}},
        )

        return {"deleted_count": result.modified_count}
