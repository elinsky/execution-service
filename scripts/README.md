# Execution Service Scripts

Utility scripts for migrating and syncing between file-based GTD system and MongoDB.

## Migration Script (`migrate.py`)

One-time migration script to import existing markdown files into MongoDB.

### Usage

```bash
python scripts/migrate.py \
  --source /path/to/execution-system \
  --mongodb-url mongodb://localhost:27017 \
  --user-id <user-id>
```

### What it does

1. **Projects**: Reads all markdown files from `10k-projects/active/**/*.md` and `10k-projects/incubator/**/*.md`
   - Parses YAML frontmatter for metadata
   - Extracts markdown content
   - Creates Project documents in MongoDB

2. **Actions**: Reads action files from `00k-next-actions/contexts/@*.md`
   - Parses todo.txt format lines
   - Extracts @context, +project tags, due dates
   - Creates Action documents in MongoDB

3. **Goals**: Reads goal files from `30k-goals/active/*.md` and `30k-goals/incubator/*.md`
   - Parses YAML frontmatter
   - Creates Goal documents in MongoDB

### Example

```bash
# Get user ID from registration
python scripts/migrate.py \
  --source ~/Dropbox/execution-system \
  --mongodb-url mongodb+srv://user:pass@cluster.mongodb.net/execution_system \
  --user-id 6733a1234567890abcdef123
```

### Output

The script will print progress for each file processed and a summary at the end:

```
=== Migration Summary ===
Projects:
  Total: 25
  Success: 24
  Failed: 1

Actions:
  Total: 150
  Success: 148
  Failed: 2

Goals:
  Total: 10
  Success: 10
  Failed: 0
```

---

## Sync Script (`sync.py`)

Bidirectional sync script to keep files and MongoDB in sync.

### Usage

```bash
# Dry run (show what would be synced)
python scripts/sync.py \
  --source /path/to/execution-system \
  --user-id <user-id> \
  --dry-run

# Real sync
python scripts/sync.py \
  --source /path/to/execution-system \
  --user-id <user-id>

# Force sync (ignore timestamps)
python scripts/sync.py \
  --source /path/to/execution-system \
  --user-id <user-id> \
  --force
```

### What it does

For each project/goal:
1. Compares file modification time with DB updated_at
2. **File newer → Update DB**: Syncs file content to database
3. **DB newer → Update file**: Writes DB content back to file
4. **Same timestamp → Skip**: No action needed

For missing items:
- **File exists, no DB → Create in DB**: Imports new file to database
- **DB exists, no file → Create file**: Exports DB record to file

### Conflict Resolution

Uses **last-write-wins** strategy:
- Whichever was modified most recently wins
- The `--force` flag syncs everything regardless of timestamps

### Scheduling

Set up a cron job to run sync every 5 minutes:

```bash
*/5 * * * * cd /path/to/execution-service && python scripts/sync.py --source /path/to/execution-system --user-id <user-id> >> /var/log/sync.log 2>&1
```

### Output

```
=== Sync Summary ===
File → DB updates: 3
DB → File updates: 2
Created in DB: 1
Created as files: 0
Skipped (same): 18
Errors: 0
```

---

## File Formats

### Project Files (10k-projects)

```markdown
---
title: Learn Rust
slug: learn-rust
area: Learning
folder: active
type: standard
created: 2024-11-01
due: 2024-12-31
last_reviewed: 2024-11-09
---

# Project content here

## Next Steps
- Read chapter 3
- Build example project
```

### Action Files (00k-next-actions/contexts)

Todo.txt format:
```
(A) 2024-11-09 Review pull request @macbook +ml-refresh due:2024-11-15
2024-11-08 Buy groceries @home
Submit report @macbook +quarterly-review due:2024-11-30
```

### Goal Files (30k-goals)

```markdown
---
title: Become a Great Leader
slug: become-a-great-leader
area: Leadership
folder: active
---

# Goal description

Focus areas:
- Public speaking
- Team building
- Strategic thinking
```

---

## Notes

- **User ID**: Get this from MongoDB after user registration via the API
- **MongoDB URL**: Use local for development, Atlas connection string for production
- **Dry Run**: Always test with `--dry-run` first to see what would change
- **Backups**: Always backup your files before running sync for the first time
- **Timestamps**: File sync relies on modification times, so don't manually edit timestamps

---

## Troubleshooting

### "Source path does not exist"
Make sure the path to your execution-system directory is correct.

### "User not found" errors
Verify the user_id is correct by checking MongoDB or creating a user via `/auth/register` endpoint.

### Sync conflicts
If you see unexpected syncs, use `--dry-run` to understand what's happening. You can use `--force` to override all timestamps.

### Permission errors
Ensure you have read/write access to both the file system and MongoDB.
