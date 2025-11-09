"""Bidirectional sync script: Keep files and MongoDB in sync.

Usage:
    # Dry run (show what would be synced)
    python scripts/sync.py --source /path/to/execution-system --dry-run

    # Real sync
    python scripts/sync.py --source /path/to/execution-system

    # Force sync (ignore timestamps, sync everything)
    python scripts/sync.py --source /path/to/execution-system --force
"""
import argparse
import asyncio
import hashlib
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime, date, timezone
import re

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.models.project import ProjectUpdate, ProjectFolder, ProjectType
from app.models.action import ActionUpdate
from app.models.goal import GoalUpdate
from app.services.project_service import ProjectService
from app.services.action_service import ActionService
from app.services.goal_service import GoalService


class FileSync:
    """Bidirectional sync between files and MongoDB."""

    def __init__(
        self,
        source_path: Path,
        mongodb_url: str,
        user_id: str,
        dry_run: bool = False,
        force: bool = False,
    ):
        """Initialize sync.

        Args:
            source_path: Path to execution-system directory
            mongodb_url: MongoDB connection URL
            user_id: User ID for documents
            dry_run: If True, don't make changes, just show what would be done
            force: If True, sync everything regardless of timestamps
        """
        self.source_path = source_path
        self.mongodb_url = mongodb_url
        self.user_id = user_id
        self.dry_run = dry_run
        self.force = force
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

        # Stats
        self.stats = {
            "file_to_db": 0,
            "db_to_file": 0,
            "created_in_db": 0,
            "created_as_file": 0,
            "skipped": 0,
            "errors": 0,
        }

    async def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(self.mongodb_url)
        self.db = self.client["execution_system"]
        if not self.dry_run:
            print(f"Connected to MongoDB: {self.mongodb_url}")

    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file content."""
        return hashlib.md5(file_path.read_bytes()).hexdigest()

    def parse_yaml_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from markdown file."""
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return {}, content

        yaml_content = match.group(1)
        markdown = match.group(2)  # Keep content exactly as-is

        metadata = {}
        for line in yaml_content.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                if key in ['due', 'created', 'started', 'completed', 'last_reviewed']:
                    if value:
                        try:
                            metadata[key] = datetime.fromisoformat(value).date()
                        except ValueError:
                            metadata[key] = value
                else:
                    metadata[key] = value

        return metadata, markdown

    def create_yaml_frontmatter(self, metadata: dict, content: str) -> str:
        """Create markdown file with YAML frontmatter.

        Uses canonical field order to ensure consistent output.
        """
        lines = ["---"]

        # Canonical field order for consistency (matches normalized markdown files)
        field_order = [
            "area", "title", "type", "created", "started",
            "last_reviewed", "due", "completed", "descoped"
        ]

        # Output fields in canonical order
        for key in field_order:
            if key in metadata and metadata[key] is not None:
                value = metadata[key]
                if isinstance(value, date):
                    lines.append(f"{key}: {value.isoformat()}")
                else:
                    lines.append(f"{key}: {value}")

        # Add any remaining fields not in canonical order (shouldn't happen normally)
        for key, value in metadata.items():
            if key not in field_order and value is not None:
                if isinstance(value, date):
                    lines.append(f"{key}: {value.isoformat()}")
                else:
                    lines.append(f"{key}: {value}")

        lines.append("---")
        lines.append(content)
        return '\n'.join(lines)

    async def sync_projects(self):
        """Sync projects between files and database."""
        print("\n=== Syncing Projects ===")

        service = ProjectService(self.db)

        # Get all projects from DB
        db_projects = await service.list_projects(user_id=self.user_id)
        db_projects_by_slug = {p.slug: p for p in db_projects}

        # Track which DB projects we've seen
        seen_slugs = set()

        # Scan file system
        for folder in ["active", "incubator"]:
            folder_path = self.source_path / "10k-projects" / folder
            if not folder_path.exists():
                continue

            for project_file in folder_path.rglob("*.md"):
                try:
                    # Get file metadata - convert to UTC for comparison with DB timestamps
                    file_mtime = datetime.fromtimestamp(project_file.stat().st_mtime, tz=timezone.utc).replace(tzinfo=None)
                    content = project_file.read_text()
                    metadata, markdown = self.parse_yaml_frontmatter(content)

                    slug = metadata.get("slug")
                    if not slug:
                        # Generate slug from filename
                        slug = project_file.stem.lower().replace(' ', '-')

                    seen_slugs.add(slug)

                    # Check if exists in DB
                    if slug in db_projects_by_slug:
                        db_project = db_projects_by_slug[slug]
                        db_mtime = db_project.updated_at

                        # Compare timestamps
                        if self.force or file_mtime > db_mtime:
                            # File is newer → update DB
                            print(f"  File → DB: {project_file.relative_to(self.source_path)}")
                            if not self.dry_run:
                                update_data = ProjectUpdate(
                                    title=metadata.get("title", db_project.title),
                                    area=metadata.get("area", db_project.area),
                                    content=markdown,
                                )
                                await service.update_project(
                                    user_id=self.user_id,
                                    slug=slug,
                                    project_update=update_data,
                                )
                            self.stats["file_to_db"] += 1

                        elif file_mtime < db_mtime:
                            # DB is newer → update file
                            print(f"  DB → File: {project_file.relative_to(self.source_path)}")
                            if not self.dry_run:
                                # Convert enums to clean strings
                                type_str = str(db_project.type)
                                if "." in type_str:
                                    type_str = type_str.split(".")[-1].lower()

                                # Only include file-native YAML fields (no DB-internal fields)
                                new_metadata = {
                                    "title": db_project.title,
                                    "area": db_project.area,
                                    "type": type_str,
                                    "created": db_project.created,
                                }
                                # Add optional date fields only if they exist
                                if db_project.last_reviewed:
                                    new_metadata["last_reviewed"] = db_project.last_reviewed
                                if db_project.due:
                                    new_metadata["due"] = db_project.due
                                if db_project.started:
                                    new_metadata["started"] = db_project.started
                                if db_project.completed:
                                    new_metadata["completed"] = db_project.completed
                                if db_project.descoped:
                                    new_metadata["descoped"] = db_project.descoped

                                new_content = self.create_yaml_frontmatter(
                                    new_metadata,
                                    db_project.content,
                                )
                                project_file.write_text(new_content)
                            self.stats["db_to_file"] += 1

                        else:
                            # Same timestamp → skip
                            self.stats["skipped"] += 1

                    else:
                        # File exists but not in DB → create in DB
                        print(f"  Create in DB: {project_file.relative_to(self.source_path)}")
                        if not self.dry_run:
                            from app.models.project import ProjectCreate
                            project_data = ProjectCreate(
                                title=metadata.get("title", project_file.stem),
                                area=metadata.get("area", "Uncategorized"),
                                folder=ProjectFolder(folder),
                                type=ProjectType(metadata.get("type", "standard")),
                                content=markdown,
                            )
                            await service.create_project(
                                user_id=self.user_id,
                                project_create=project_data,
                            )
                        self.stats["created_in_db"] += 1

                except Exception as e:
                    print(f"  Error syncing {project_file.relative_to(self.source_path)}: {e}")
                    self.stats["errors"] += 1

        # Check for DB projects without files
        for slug, db_project in db_projects_by_slug.items():
            if slug not in seen_slugs and not db_project.deleted:
                # DB project without file → create file
                folder = str(db_project.folder)
                # Handle enum representation (e.g., "ProjectFolder.ACTIVE" -> "active")
                if "." in folder:
                    folder = folder.split(".")[-1].lower()
                folder_path = self.source_path / "10k-projects" / folder
                folder_path.mkdir(parents=True, exist_ok=True)

                # Create file path from title
                filename = db_project.slug + ".md"
                file_path = folder_path / filename

                print(f"  Create file: 10k-projects/{folder}/{filename}")
                if not self.dry_run:
                    # Convert enums to clean strings
                    type_str = str(db_project.type)
                    if "." in type_str:
                        type_str = type_str.split(".")[-1].lower()

                    # Only include file-native YAML fields
                    metadata = {
                        "title": db_project.title,
                        "area": db_project.area,
                        "type": type_str,
                        "created": db_project.created,
                    }
                    # Add optional date fields only if they exist
                    if db_project.last_reviewed:
                        metadata["last_reviewed"] = db_project.last_reviewed
                    if db_project.due:
                        metadata["due"] = db_project.due
                    if db_project.started:
                        metadata["started"] = db_project.started
                    if db_project.completed:
                        metadata["completed"] = db_project.completed
                    if db_project.descoped:
                        metadata["descoped"] = db_project.descoped

                    content = self.create_yaml_frontmatter(metadata, db_project.content)
                    file_path.write_text(content)
                self.stats["created_as_file"] += 1

    async def sync_goals(self):
        """Sync goals between files and database."""
        print("\n=== Syncing Goals ===")

        service = GoalService(self.db)

        # Get all goals from DB
        db_goals = await service.list_goals(user_id=self.user_id)
        db_goals_by_slug = {g.slug: g for g in db_goals}

        seen_slugs = set()

        # Scan file system
        for folder in ["active", "incubator"]:
            folder_path = self.source_path / "30k-goals" / folder
            if not folder_path.exists():
                continue

            for goal_file in folder_path.glob("*.md"):
                try:
                    # Get file metadata - convert to UTC for comparison with DB timestamps
                    file_mtime = datetime.fromtimestamp(goal_file.stat().st_mtime, tz=timezone.utc).replace(tzinfo=None)
                    content = goal_file.read_text()
                    metadata, markdown = self.parse_yaml_frontmatter(content)

                    slug = metadata.get("slug") or goal_file.stem.lower().replace(' ', '-')
                    seen_slugs.add(slug)

                    if slug in db_goals_by_slug:
                        db_goal = db_goals_by_slug[slug]
                        db_mtime = db_goal.updated_at

                        if self.force or file_mtime > db_mtime:
                            print(f"  File → DB: {goal_file.relative_to(self.source_path)}")
                            if not self.dry_run:
                                update_data = GoalUpdate(
                                    title=metadata.get("title", db_goal.title),
                                    area=metadata.get("area", db_goal.area),
                                    content=markdown,
                                )
                                await service.update_goal(
                                    user_id=self.user_id,
                                    slug=slug,
                                    goal_update=update_data,
                                )
                            self.stats["file_to_db"] += 1
                        elif file_mtime < db_mtime:
                            print(f"  DB → File: {goal_file.relative_to(self.source_path)}")
                            if not self.dry_run:
                                # Only include file-native YAML fields (no DB-internal fields)
                                new_metadata = {
                                    "title": db_goal.title,
                                    "area": db_goal.area,
                                }
                                # Add optional date fields only if they exist
                                if db_goal.last_reviewed:
                                    new_metadata["last_reviewed"] = db_goal.last_reviewed
                                if db_goal.created:
                                    new_metadata["created"] = db_goal.created

                                new_content = self.create_yaml_frontmatter(
                                    new_metadata,
                                    db_goal.content,
                                )
                                goal_file.write_text(new_content)
                            self.stats["db_to_file"] += 1
                        else:
                            self.stats["skipped"] += 1

                    else:
                        print(f"  Create in DB: {goal_file.relative_to(self.source_path)}")
                        if not self.dry_run:
                            from app.models.goal import GoalCreate
                            goal_data = GoalCreate(
                                title=metadata.get("title", goal_file.stem),
                                area=metadata.get("area", "Uncategorized"),
                                content=markdown,
                            )
                            await service.create_goal(
                                user_id=self.user_id,
                                goal_create=goal_data,
                            )
                        self.stats["created_in_db"] += 1

                except Exception as e:
                    print(f"  Error syncing {goal_file.relative_to(self.source_path)}: {e}")
                    self.stats["errors"] += 1

        # Create files for DB goals without files
        for slug, db_goal in db_goals_by_slug.items():
            if slug not in seen_slugs and not db_goal.deleted:
                folder = str(db_goal.folder)
                # Handle enum representation (e.g., "ProjectFolder.ACTIVE" -> "active")
                if "." in folder:
                    folder = folder.split(".")[-1].lower()
                folder_path = self.source_path / "30k-goals" / folder
                folder_path.mkdir(parents=True, exist_ok=True)

                filename = db_goal.slug + ".md"
                file_path = folder_path / filename

                print(f"  Create file: 30k-goals/{folder}/{filename}")
                if not self.dry_run:
                    # Only include file-native YAML fields
                    metadata = {
                        "title": db_goal.title,
                        "area": db_goal.area,
                    }
                    # Add optional date fields only if they exist
                    if db_goal.last_reviewed:
                        metadata["last_reviewed"] = db_goal.last_reviewed
                    if db_goal.created:
                        metadata["created"] = db_goal.created

                    content = self.create_yaml_frontmatter(metadata, db_goal.content)
                    file_path.write_text(content)
                self.stats["created_as_file"] += 1

    async def run(self):
        """Run sync."""
        mode = "DRY RUN" if self.dry_run else "SYNC"
        print(f"=== {mode} MODE ===")
        print(f"Source: {self.source_path}")
        print(f"User ID: {self.user_id}")

        await self.connect()

        try:
            await self.sync_projects()
            await self.sync_goals()

            # Print summary
            print("\n=== Sync Summary ===")
            print(f"File → DB updates: {self.stats['file_to_db']}")
            print(f"DB → File updates: {self.stats['db_to_file']}")
            print(f"Created in DB: {self.stats['created_in_db']}")
            print(f"Created as files: {self.stats['created_as_file']}")
            print(f"Skipped (same): {self.stats['skipped']}")
            print(f"Errors: {self.stats['errors']}")

            if self.dry_run:
                print("\n(Dry run - no changes made)")

        finally:
            await self.close()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Bidirectional sync between files and MongoDB")
    parser.add_argument(
        "--source",
        required=True,
        help="Path to execution-system directory",
    )
    parser.add_argument(
        "--mongodb-url",
        default="mongodb://localhost:27017",
        help="MongoDB connection URL",
    )
    parser.add_argument(
        "--user-id",
        required=True,
        help="User ID for documents",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force sync all files regardless of timestamps",
    )

    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: Source path does not exist: {source_path}")
        sys.exit(1)

    sync = FileSync(
        source_path=source_path,
        mongodb_url=args.mongodb_url,
        user_id=args.user_id,
        dry_run=args.dry_run,
        force=args.force,
    )

    await sync.run()


if __name__ == "__main__":
    asyncio.run(main())
