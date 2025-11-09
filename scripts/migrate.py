"""One-time migration script: Import markdown files into MongoDB.

Usage:
    python scripts/migrate.py \\
        --source /path/to/execution-system \\
        --mongodb-url mongodb://localhost:27017 \\
        --user-id <user-id>
"""
import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional
import re
from datetime import datetime, date

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.models.project import ProjectCreate, ProjectFolder, ProjectType
from app.models.action import ActionCreate
from app.models.goal import GoalCreate
from app.services.project_service import ProjectService
from app.services.action_service import ActionService
from app.services.goal_service import GoalService


class FileMigrator:
    """Migrates markdown files to MongoDB."""

    def __init__(self, source_path: Path, mongodb_url: str, user_id: str):
        """Initialize migrator.

        Args:
            source_path: Path to execution-system directory
            mongodb_url: MongoDB connection URL
            user_id: User ID for all imported documents
        """
        self.source_path = source_path
        self.mongodb_url = mongodb_url
        self.user_id = user_id
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None

        # Stats
        self.stats = {
            "projects": {"total": 0, "success": 0, "failed": 0},
            "actions": {"total": 0, "success": 0, "failed": 0},
            "goals": {"total": 0, "success": 0, "failed": 0},
        }

    async def connect(self):
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(self.mongodb_url)
        self.db = self.client["execution_system"]
        print(f"Connected to MongoDB: {self.mongodb_url}")

    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            print("Closed MongoDB connection")

    def parse_yaml_frontmatter(self, content: str) -> tuple[dict, str]:
        """Parse YAML frontmatter from markdown file.

        Args:
            content: File content

        Returns:
            Tuple of (metadata dict, markdown content)
        """
        # Match YAML frontmatter between --- delimiters
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return {}, content

        yaml_content = match.group(1)
        markdown = match.group(2)  # Keep content exactly as-is

        # Parse YAML (simple key: value parser)
        metadata = {}
        for line in yaml_content.split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                # Parse dates
                if key in ['due', 'created', 'started', 'completed', 'last_reviewed', 'descoped']:
                    if value:
                        try:
                            metadata[key] = datetime.fromisoformat(value).date()
                        except ValueError:
                            metadata[key] = value
                else:
                    metadata[key] = value

        return metadata, markdown

    async def migrate_projects(self):
        """Migrate project files from 10k-projects/."""
        print("\n=== Migrating Projects ===")

        service = ProjectService(self.db)

        # Find all project markdown files
        for folder in ["active", "incubator", "completed", "descoped"]:
            folder_path = self.source_path / "10k-projects" / folder
            if not folder_path.exists():
                print(f"  Skipping {folder}: directory not found")
                continue

            # Process all markdown files recursively
            for project_file in folder_path.rglob("*.md"):
                self.stats["projects"]["total"] += 1

                try:
                    # Read file
                    content = project_file.read_text()
                    metadata, markdown = self.parse_yaml_frontmatter(content)

                    # Extract title from metadata or filename
                    title = metadata.get("title", project_file.stem)
                    area = metadata.get("area", "Uncategorized")

                    # Create project
                    project_data = ProjectCreate(
                        title=title,
                        area=area,
                        folder=ProjectFolder(folder) if folder in ["active", "incubator"] else ProjectFolder.ACTIVE,
                        type=ProjectType(metadata.get("type", "standard")),
                        content=markdown,
                        due=metadata.get("due") if isinstance(metadata.get("due"), date) else None,
                        created=metadata.get("created") if isinstance(metadata.get("created"), date) else None,
                        started=metadata.get("started") if isinstance(metadata.get("started"), date) else None,
                        last_reviewed=metadata.get("last_reviewed") if isinstance(metadata.get("last_reviewed"), date) else None,
                        completed=metadata.get("completed") if isinstance(metadata.get("completed"), date) else None,
                        descoped=metadata.get("descoped") if isinstance(metadata.get("descoped"), date) else None,
                    )

                    await service.create_project(
                        user_id=self.user_id,
                        project_create=project_data,
                    )

                    self.stats["projects"]["success"] += 1
                    print(f"  ✓ {project_file.relative_to(self.source_path)}")

                except Exception as e:
                    self.stats["projects"]["failed"] += 1
                    print(f"  ✗ {project_file.relative_to(self.source_path)}: {e}")

    def parse_todo_txt_line(self, line: str) -> Optional[dict]:
        """Parse a todo.txt format line.

        Format: (A) 2024-11-09 Action text @context +project due:2024-12-31

        Args:
            line: Single line from action file

        Returns:
            Dict with action data or None if not a valid action
        """
        line = line.strip()
        if not line or line.startswith('#'):
            return None

        # Extract components
        action_data = {
            "text": line,
            "context": None,
            "project_slug": None,
            "due": None,
            "defer": None,
            "action_date": None,
            "state": "next",
        }

        # Extract @context
        context_match = re.search(r'@(\S+)', line)
        if context_match:
            action_data["context"] = f"@{context_match.group(1)}"

        # Extract +project
        project_match = re.search(r'\+(\S+)', line)
        if project_match:
            action_data["project_slug"] = project_match.group(1)

        # Extract due: date
        due_match = re.search(r'due:(\d{4}-\d{2}-\d{2})', line)
        if due_match:
            try:
                action_data["due"] = datetime.strptime(due_match.group(1), '%Y-%m-%d').date()
            except ValueError:
                pass

        # Extract defer: date
        defer_match = re.search(r'defer:(\d{4}-\d{2}-\d{2})', line)
        if defer_match:
            try:
                action_data["defer"] = datetime.strptime(defer_match.group(1), '%Y-%m-%d').date()
            except ValueError:
                pass

        # Extract action date (format: YYYY-MM-DD at start or after priority)
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
        if date_match:
            try:
                action_data["action_date"] = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
            except ValueError:
                pass

        # Clean text (remove tags and dates that were extracted)
        text = re.sub(r'@\S+', '', line)  # Remove @context
        text = re.sub(r'\+\S+', '', text)  # Remove +project
        text = re.sub(r'due:\S+', '', text)  # Remove due:
        text = re.sub(r'defer:\S+', '', text)  # Remove defer:
        text = re.sub(r'^\(\w\)\s*', '', text)  # Remove priority
        text = re.sub(r'^\d{4}-\d{2}-\d{2}\s*', '', text)  # Remove leading date
        text = re.sub(r'\s+', ' ', text).strip()  # Clean whitespace

        action_data["text"] = text

        return action_data if text else None

    async def migrate_actions(self):
        """Migrate action files from 00k-next-actions/contexts/."""
        print("\n=== Migrating Actions ===")

        service = ActionService(self.db)

        contexts_path = self.source_path / "00k-next-actions" / "contexts"
        if not contexts_path.exists():
            print(f"  Skipping: {contexts_path} not found")
            return

        # Process each context file
        for action_file in contexts_path.glob("@*.md"):
            try:
                content = action_file.read_text()
                _, markdown = self.parse_yaml_frontmatter(content)

                # Parse each line as a todo.txt action
                for line in markdown.split('\n'):
                    action_data = self.parse_todo_txt_line(line)
                    if not action_data:
                        continue

                    self.stats["actions"]["total"] += 1

                    try:
                        # Determine context from filename if not in line
                        if not action_data["context"]:
                            action_data["context"] = action_file.stem  # @macbook, @waiting, etc

                        # Create action
                        action_create = ActionCreate(
                            text=action_data["text"],
                            context=action_data["context"],
                            project_slug=action_data["project_slug"],
                            due=action_data["due"],
                            defer=action_data["defer"],
                            action_date=action_data["action_date"] or date.today(),
                        )

                        await service.create_action(
                            user_id=self.user_id,
                            action_create=action_create,
                        )

                        self.stats["actions"]["success"] += 1

                    except Exception as e:
                        self.stats["actions"]["failed"] += 1
                        print(f"  ✗ Failed to create action: {action_data['text'][:50]}... ({e})")

                print(f"  ✓ {action_file.relative_to(self.source_path)}")

            except Exception as e:
                print(f"  ✗ {action_file.relative_to(self.source_path)}: {e}")

    async def migrate_goals(self):
        """Migrate goal files from 30k-goals/."""
        print("\n=== Migrating Goals ===")

        service = GoalService(self.db)

        # Find all goal markdown files
        for folder in ["active", "incubator"]:
            folder_path = self.source_path / "30k-goals" / folder
            if not folder_path.exists():
                print(f"  Skipping {folder}: directory not found")
                continue

            for goal_file in folder_path.glob("*.md"):
                self.stats["goals"]["total"] += 1

                try:
                    # Read file
                    content = goal_file.read_text()
                    metadata, markdown = self.parse_yaml_frontmatter(content)

                    # Extract title from metadata or filename
                    title = metadata.get("title", goal_file.stem)
                    area = metadata.get("area", "Uncategorized")

                    # Create goal
                    goal_data = GoalCreate(
                        title=title,
                        area=area,
                        content=markdown,
                    )

                    await service.create_goal(
                        user_id=self.user_id,
                        goal_create=goal_data,
                    )

                    self.stats["goals"]["success"] += 1
                    print(f"  ✓ {goal_file.relative_to(self.source_path)}")

                except Exception as e:
                    self.stats["goals"]["failed"] += 1
                    print(f"  ✗ {goal_file.relative_to(self.source_path)}: {e}")

    async def run(self):
        """Run migration."""
        print(f"Starting migration from {self.source_path}")
        print(f"User ID: {self.user_id}")

        await self.connect()

        try:
            await self.migrate_projects()
            await self.migrate_actions()
            await self.migrate_goals()

            # Print summary
            print("\n=== Migration Summary ===")
            for entity_type, stats in self.stats.items():
                print(f"{entity_type.capitalize()}:")
                print(f"  Total: {stats['total']}")
                print(f"  Success: {stats['success']}")
                print(f"  Failed: {stats['failed']}")

        finally:
            await self.close()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate markdown files to MongoDB")
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
        help="User ID for all imported documents",
    )

    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: Source path does not exist: {source_path}")
        sys.exit(1)

    migrator = FileMigrator(
        source_path=source_path,
        mongodb_url=args.mongodb_url,
        user_id=args.user_id,
    )

    await migrator.run()


if __name__ == "__main__":
    asyncio.run(main())
