# Execution Service Implementation Plan

**Status:** Phase 3 - Authentication
**Start Date:** 2025-11-09
**Last Updated:** 2025-11-09
**Tech Stack:** FastAPI, MongoDB Atlas, Python 3.11+, pytest (TDD)

---

## Overview

This plan outlines the step-by-step implementation of the execution-service backend API. We follow Test-Driven Development (TDD) principles: write tests first, then implement features to pass those tests.

**Key Principles:**
- **TDD:** Write failing tests → implement code → pass tests → refactor
- **Iterative:** Build in small, testable increments
- **MVP-first:** Core features before advanced features
- **Deploy early:** Get to production quickly, iterate from there

---

## Phase 1: Project Setup & Infrastructure (Day 1)

### 1.1 MongoDB Atlas Setup
**Goal:** Cloud database ready to use

- [x] Create MongoDB Atlas account
- [x] Create free M0 cluster
- [x] Create database: `execution_system`
- [ ] Create collections: `users`, `projects`, `actions`, `time_entries`, `goals`
- [x] Create database user with credentials
- [x] Whitelist development IP address
- [x] Get connection string
- [x] Test connection with Motor client

**Deliverable:** Working MongoDB connection string (Complete)

---

### 1.2 Repository Scaffolding
**Goal:** FastAPI project structure with TDD setup

**Directory Structure:**
```
execution-service/
├── .env.example
├── .gitignore
├── pyproject.toml           # uv package manager
├── README.md
├── ARCHITECTURE.md           # Already created
├── IMPLEMENTATION_PLAN.md    # This file
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings (Pydantic BaseSettings)
│   ├── database.py          # MongoDB connection
│   ├── models/              # Pydantic models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── action.py
│   │   ├── time_entry.py
│   │   └── goal.py
│   ├── routers/             # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── projects.py
│   │   ├── actions.py
│   │   ├── timers.py
│   │   └── goals.py
│   ├── services/            # Business logic
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── project_service.py
│   │   ├── action_service.py
│   │   ├── timer_service.py
│   │   └── sync_service.py
│   └── utils/               # Helpers
│       ├── __init__.py
│       ├── slug.py          # Slug generation
│       ├── auth.py          # JWT helpers
│       └── validators.py    # Custom validators
├── scripts/
│   ├── migrate.py           # One-time migration: files → MongoDB
│   └── sync.py              # Bidirectional sync script
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # pytest fixtures
│   ├── test_models.py
│   ├── unit/
│   │   ├── test_auth_service.py
│   │   ├── test_project_service.py
│   │   ├── test_action_service.py
│   │   └── test_timer_service.py
│   └── integration/
│       ├── test_auth_endpoints.py
│       ├── test_project_endpoints.py
│       ├── test_action_endpoints.py
│       └── test_timer_endpoints.py
└── .github/
    └── workflows/
        └── test.yml         # GitHub Actions CI
```

**Tasks:**
- [x] Initialize git repo (already exists)
- [x] Create `pyproject.toml` with dependencies
- [x] Add dependencies: fastapi, uvicorn, motor, pydantic, python-jose, passlib, pytest, httpx
- [x] Create `.env.example` with MongoDB URL, JWT secret
- [x] Create `.gitignore` (Python, env files, __pycache__)
- [x] Create directory structure
- [x] Create empty `__init__.py` files
- [x] Set up pytest configuration in `pyproject.toml`

**Test:**
```bash
# Using pyenv virtualenv (not uv)
~/.pyenv/versions/execution-service/bin/pytest  # Passes (2 tests)
~/.pyenv/versions/execution-service/bin/python -c "from app import main; print('Import works')"
```

**Deliverable:** Project structure ready, dependencies installed (Complete)

---

## Phase 2: Database Models & Connection (Day 1-2)

### 2.1 Database Connection
**Goal:** Motor async MongoDB client ready

**File:** `app/database.py`

**TDD Steps:**
1. **Write test:** `tests/test_database.py`
   - Test connection succeeds
   - Test ping command
   - Test database/collection access

2. **Implement:**
   ```python
   from motor.motor_asyncio import AsyncIOMotorClient
   from app.config import settings

   class Database:
       client: AsyncIOMotorClient = None

   db = Database()

   async def connect_db():
       db.client = AsyncIOMotorClient(settings.MONGODB_URL)
       await db.client.admin.command('ping')

   async def close_db():
       db.client.close()

   def get_database():
       return db.client[settings.DB_NAME]
   ```

3. **Test passes:** Connection works

**Tasks:**
- [x] Write `test_database.py` tests (basic health check tests)
- [x] Implement `database.py`
- [x] Create `config.py` with Pydantic BaseSettings
- [x] All tests pass

---

### 2.2 Pydantic Models
**Goal:** Type-safe data models for all collections

**Files:** `app/models/*.py`

**TDD Steps:**
1. **Write tests:** `tests/test_models.py`
   - Test User model validation
   - Test Project model validation (all fields, enums)
   - Test Action model validation (todo.txt format)
   - Test TimeEntry model validation
   - Test Goal model validation
   - Test soft delete fields
   - Test slug generation

2. **Implement models:**

**Example:** `app/models/project.py`
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from enum import Enum

class ProjectFolder(str, Enum):
    ACTIVE = "active"
    INCUBATOR = "incubator"
    COMPLETED = "completed"
    DESCOPED = "descoped"

class ProjectType(str, Enum):
    STANDARD = "standard"
    COORDINATION = "coordination"
    HABIT = "habit"
    GOAL = "goal"

class ProjectBase(BaseModel):
    title: str
    area: str
    folder: ProjectFolder = ProjectFolder.ACTIVE
    type: ProjectType = ProjectType.STANDARD
    due: Optional[date] = None
    content: str = ""

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    area: Optional[str] = None
    folder: Optional[ProjectFolder] = None
    due: Optional[date] = None
    content: Optional[str] = None

class Project(ProjectBase):
    id: str = Field(alias="_id")
    user_id: str
    slug: str
    created: date
    started: Optional[date] = None
    last_reviewed: Optional[date] = None
    completed: Optional[date] = None
    descoped: Optional[date] = None
    deleted: bool = False
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True
```

**Similar for:**
- `app/models/user.py` (User, UserCreate, UserInDB)
- `app/models/action.py` (Action, ActionCreate, ActionUpdate)
- `app/models/time_entry.py` (TimeEntry, TimeEntryCreate)
- `app/models/goal.py` (Goal, GoalCreate, GoalUpdate)

**Tasks:**
- [x] Write model tests for all entities
- [x] Implement User model
- [x] Implement Project model
- [x] Implement Action model
- [x] Implement TimeEntry model
- [x] Implement Goal model
- [x] All validation tests pass

---

### 2.3 Utilities
**Goal:** Helper functions for slug, auth, validation

**File:** `app/utils/slug.py`

**TDD Steps:**
1. **Write tests:** `tests/unit/test_slug.py`
   - "Learn Rust" → "learn-rust"
   - "DE Shaw TPM Role" → "de-shaw-tpm-role"
   - Special characters removed
   - Unique slug generation with suffix

2. **Implement:**
   ```python
   import re
   from typing import Optional

   def slugify(text: str) -> str:
       """Convert text to URL-safe slug"""
       slug = text.lower().strip()
       slug = re.sub(r'[^\w\s-]', '', slug)
       slug = re.sub(r'[\s_-]+', '-', slug)
       slug = re.sub(r'^-+|-+$', '', slug)
       return slug

   async def generate_unique_slug(
       collection,
       base_slug: str,
       user_id: str,
       exclude_id: Optional[str] = None
   ) -> str:
       """Generate unique slug with numeric suffix if needed"""
       # Implementation with MongoDB query
   ```

**Similar for:**
- `app/utils/auth.py` (JWT creation, verification, password hashing)
- `app/utils/validators.py` (Custom validators)

**Tasks:**
- [x] Write slug tests
- [x] Implement slug.py
- [x] Write auth tests (JWT, password)
- [x] Implement auth.py
- [x] All utils tests pass

---

## Phase 3: Authentication (Day 2-3)

### 3.1 Auth Service (Business Logic)
**Goal:** User registration, login, token generation

**File:** `app/services/auth_service.py`

**TDD Steps:**
1. **Write tests:** `tests/unit/test_auth_service.py`
   - Test user registration (hash password, create user)
   - Test duplicate email detection
   - Test login (verify password, generate JWT)
   - Test invalid credentials
   - Test API key generation
   - Test token verification

2. **Implement service:**
   ```python
   from passlib.context import CryptContext
   from jose import jwt
   from datetime import datetime, timedelta

   class AuthService:
       def __init__(self, db):
           self.db = db
           self.pwd_context = CryptContext(schemes=["bcrypt"])

       async def register_user(self, email: str, password: str, name: str):
           # Hash password
           # Check for existing user
           # Create user document
           # Return user

       async def login(self, email: str, password: str):
           # Find user
           # Verify password
           # Generate JWT token
           # Return token

       async def verify_token(self, token: str):
           # Decode JWT
           # Return user_id
   ```

**Tasks:**
- [ ] Write auth service tests
- [ ] Implement AuthService
- [ ] All service tests pass

---

### 3.2 Auth Router (API Endpoints)
**Goal:** `/auth` endpoints working

**File:** `app/routers/auth.py`

**Endpoints:**
- `POST /auth/register` - Create new user
- `POST /auth/login` - Login, get JWT token
- `GET /auth/me` - Get current user info

**TDD Steps:**
1. **Write tests:** `tests/integration/test_auth_endpoints.py`
   - Test POST /auth/register (success)
   - Test POST /auth/register (duplicate email)
   - Test POST /auth/login (success)
   - Test POST /auth/login (wrong password)
   - Test GET /auth/me (with token)
   - Test GET /auth/me (no token → 401)

2. **Implement router:**
   ```python
   from fastapi import APIRouter, Depends, HTTPException
   from app.services.auth_service import AuthService
   from app.models.user import UserCreate, User

   router = APIRouter(prefix="/auth", tags=["auth"])

   @router.post("/register")
   async def register(user: UserCreate):
       # Call AuthService.register_user
       # Return user (without password)

   @router.post("/login")
   async def login(credentials):
       # Call AuthService.login
       # Return JWT token

   @router.get("/me")
   async def get_current_user(user_id: str = Depends(verify_token)):
       # Get user from DB
       # Return user
   ```

3. **Wire up in main.py:**
   ```python
   from app.routers import auth

   app = FastAPI()
   app.include_router(auth.router)
   ```

**Tasks:**
- [ ] Write auth endpoint tests
- [ ] Implement auth router
- [ ] Wire up in main.py
- [ ] All integration tests pass
- [ ] Manual test with curl/httpx

**Manual Test:**
```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"brian@example.com","password":"test123","name":"Brian"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"brian@example.com","password":"test123"}'

# Get current user (with token)
curl http://localhost:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

---

## Phase 4: Projects CRUD (Day 3-5)

### 4.1 Project Service
**Goal:** All project business logic in service layer

**File:** `app/services/project_service.py`

**TDD Steps:**
1. **Write tests:** `tests/unit/test_project_service.py`
   - Test create_project (slug generation, validation)
   - Test create_project (duplicate slug → error)
   - Test list_projects (folder filter)
   - Test list_projects (area filter)
   - Test list_projects (deleted excluded)
   - Test get_project_by_slug
   - Test update_project (content, metadata)
   - Test update_project (title change → new slug)
   - Test complete_project (has incomplete actions → error)
   - Test complete_project (success)
   - Test delete_project (soft delete)
   - Test activate_project
   - Test move_to_incubator (has actions → error)
   - Test descope_project

2. **Implement service:**
   ```python
   class ProjectService:
       def __init__(self, db):
           self.db = db
           self.collection = db.projects

       async def create_project(
           self,
           user_id: str,
           project_create: ProjectCreate
       ) -> Project:
           # Generate slug
           # Check unique slug
           # Create document with all fields
           # Insert into MongoDB
           # Return Project

       async def list_projects(
           self,
           user_id: str,
           folder: Optional[str] = None,
           area: Optional[str] = None
       ) -> List[Project]:
           # Build query with filters
           # Always filter deleted: false
           # Sort by last_reviewed desc
           # Return projects

       async def update_project(
           self,
           user_id: str,
           slug: str,
           updates: ProjectUpdate
       ) -> Project:
           # Find project (deleted: false)
           # If title changed, regenerate slug
           # Update document
           # Return updated project

       async def delete_project(
           self,
           user_id: str,
           slug: str
       ) -> dict:
           # Soft delete project
           # Soft delete associated actions
           # Return count

       # ... other methods
   ```

**Tasks:**
- [ ] Write all project service tests
- [ ] Implement ProjectService.create_project
- [ ] Implement ProjectService.list_projects
- [ ] Implement ProjectService.get_project
- [ ] Implement ProjectService.update_project
- [ ] Implement ProjectService.delete_project
- [ ] Implement ProjectService.complete_project
- [ ] Implement ProjectService.activate_project
- [ ] All service tests pass

---

### 4.2 Project Router
**Goal:** All `/projects` endpoints working

**File:** `app/routers/projects.py`

**Endpoints:**
- `GET /projects` - List projects with filters
- `POST /projects` - Create new project
- `GET /projects/:slug` - Get single project
- `PATCH /projects/:slug` - Update project
- `DELETE /projects/:slug` - Soft delete project
- `POST /projects/:slug/complete` - Complete project
- `POST /projects/:slug/activate` - Activate from incubator
- `POST /projects/:slug/descope` - Descope project

**TDD Steps:**
1. **Write tests:** `tests/integration/test_project_endpoints.py`
   - Test GET /projects (authenticated)
   - Test GET /projects (filter by folder)
   - Test GET /projects (filter by area)
   - Test GET /projects (unauthenticated → 401)
   - Test POST /projects (create success)
   - Test POST /projects (duplicate slug → 409)
   - Test GET /projects/:slug (found)
   - Test GET /projects/:slug (not found → 404)
   - Test PATCH /projects/:slug (update content)
   - Test PATCH /projects/:slug (update title → new slug)
   - Test DELETE /projects/:slug (success)
   - Test POST /projects/:slug/complete (has actions → 400)
   - Test POST /projects/:slug/complete (success)

2. **Implement router:**
   ```python
   from fastapi import APIRouter, Depends, HTTPException, Query
   from app.services.project_service import ProjectService
   from app.models.project import Project, ProjectCreate, ProjectUpdate

   router = APIRouter(prefix="/projects", tags=["projects"])

   @router.get("")
   async def list_projects(
       folder: Optional[str] = Query(None),
       area: Optional[str] = Query(None),
       user_id: str = Depends(get_current_user_id)
   ):
       service = ProjectService(get_database())
       projects = await service.list_projects(user_id, folder, area)
       return {"projects": projects, "total": len(projects)}

   @router.post("", status_code=201)
   async def create_project(
       project: ProjectCreate,
       user_id: str = Depends(get_current_user_id)
   ):
       service = ProjectService(get_database())
       return await service.create_project(user_id, project)

   # ... other endpoints
   ```

**Tasks:**
- [ ] Write all project endpoint tests
- [ ] Implement all project endpoints
- [ ] Wire up in main.py
- [ ] All integration tests pass
- [ ] Manual API testing

---

## Phase 5: Actions CRUD (Day 5-6)

### 5.1 Action Service
**Goal:** All action business logic

**File:** `app/services/action_service.py`

**Methods:**
- `create_action(user_id, action_create)` - Validate project exists
- `list_actions(user_id, context, completed)` - Filter by context
- `update_action(user_id, action_id, updates)` - Edit text/metadata
- `complete_action(user_id, action_id)` - Mark complete
- `delete_action(user_id, action_id)` - Soft delete

**TDD approach same as projects:**
1. Write service tests
2. Implement service
3. Write endpoint tests
4. Implement router
5. All tests pass

**Tasks:**
- [ ] Write action service tests
- [ ] Implement ActionService
- [ ] Write action endpoint tests
- [ ] Implement action router (`app/routers/actions.py`)
- [ ] All tests pass

**Key Validation:**
- When creating action with `+project`, validate project exists
- When completing project, check no incomplete actions exist
- Filter out soft-deleted actions by default

---

## Phase 6: Time Tracking (Day 6-7)

### 6.1 Timer Service
**Goal:** Start/stop timers, calculate duration

**File:** `app/services/timer_service.py`

**Methods:**
- `start_timer(user_id, project_id, description)` - Create entry with start_time
- `stop_timer(user_id)` - Find running timer, set end_time, calculate duration
- `get_current_timer(user_id)` - Get running timer or None
- `list_entries(user_id, start_date, end_date)` - Get time entries
- `get_weekly_summary(user_id, week_start)` - Aggregate by project
- `update_time_stats(project_id)` - Denormalize stats on project

**TDD Steps:**
1. Write timer service tests
2. Implement TimerService
3. Write timer endpoint tests
4. Implement timer router (`app/routers/timers.py`)
5. All tests pass

**Endpoints:**
- `POST /timers/start` - Start timer
- `POST /timers/stop` - Stop current timer
- `GET /timers/current` - Get current timer
- `GET /entries` - List time entries
- `POST /entries` - Manual time entry
- `GET /reports/summary` - Weekly/daily summaries

**Tasks:**
- [ ] Write timer service tests
- [ ] Implement TimerService
- [ ] Write timer endpoint tests
- [ ] Implement timer router
- [ ] All tests pass

---

## Phase 7: Goals (Day 7)

**Goal:** 30k-level goal operations

**Quick implementation (similar to projects):**
- [ ] GoalService (`app/services/goal_service.py`)
- [ ] Goal router (`app/routers/goals.py`)
- [ ] Tests for both
- [ ] Endpoints: GET /goals, POST /goals, PATCH /goals/:slug

---

## Phase 8: File Sync Script (Day 8-9)

### 8.1 Migration Script (One-time)
**Goal:** Import existing markdown files into MongoDB

**File:** `scripts/migrate.py`

**Tasks:**
- [ ] Read all project files from `10k-projects/active/**/*.md`
- [ ] Parse YAML frontmatter + markdown content
- [ ] Create Project documents in MongoDB
- [ ] Read all action files from `00k-next-actions/contexts/@*.md`
- [ ] Parse todo.txt format
- [ ] Create Action documents in MongoDB
- [ ] Read goals from `30k-goals/active/*.md`
- [ ] Create Goal documents
- [ ] Log migration results

**Run once:**
```bash
uv run python scripts/migrate.py \
  --source /path/to/execution-system \
  --mongodb-url $MONGODB_URL \
  --user-id <brian-user-id>
```

---

### 8.2 Bidirectional Sync Script
**Goal:** Keep files and DB in sync

**File:** `scripts/sync.py`

**Logic:**
1. For each project file:
   - Get file mtime and hash
   - Get DB document's sync metadata
   - Compare timestamps:
     - File newer → update DB from file
     - DB newer → update file from DB
     - Same → skip
2. For each DB project without file:
   - Create file from DB
3. For each file without DB project:
   - Create DB document from file

**Last-write-wins conflict resolution**

**Tasks:**
- [ ] Write sync script
- [ ] Test file → DB sync
- [ ] Test DB → file sync
- [ ] Test conflict resolution
- [ ] Add CLI options (--dry-run, --force)

**Run:**
```bash
# Dry run
uv run python scripts/sync.py \
  --source /path/to/execution-system \
  --dry-run

# Real sync
uv run python scripts/sync.py \
  --source /path/to/execution-system
```

**Cron job (every 5 minutes):**
```bash
*/5 * * * * cd /path/to/execution-service && uv run python scripts/sync.py --source /path/to/execution-system
```

---

## Phase 9: MCP Integration (Day 9-10)

### 9.1 Update execution-system-mcp
**Goal:** MCP tools call API instead of reading files

**File:** `execution-system-mcp/src/execution_system_mcp/server.py`

**Changes:**
- Replace file I/O with HTTP calls to `execution-service` API
- Add API URL + JWT token to config
- Update all 31 handler functions:
  - `create_project` → POST /api/projects
  - `list_projects` → GET /api/projects
  - `add_action` → POST /api/actions
  - etc.

**Tasks:**
- [ ] Add httpx dependency to execution-system-mcp
- [ ] Create API client class
- [ ] Update create_project handler
- [ ] Update list_projects handler
- [ ] Update add_action handler
- [ ] Update complete_project handler
- [ ] Test all tools work via API
- [ ] Update README with new config

**Config:** `~/.config/execution-service/config.json`
```json
{
  "api_url": "http://localhost:8000",
  "jwt_token": "your-jwt-token-here"
}
```

---

## Phase 10: Deployment (Day 10-11)

### 10.1 GCP Cloud Run Setup
**Goal:** API deployed and accessible

**Tasks:**
- [ ] Create `Dockerfile`:
  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY pyproject.toml .
  RUN pip install uv && uv sync
  COPY app/ app/
  CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
  ```
- [ ] Build and test locally:
  ```bash
  docker build -t execution-service .
  docker run -p 8080:8080 execution-service
  ```
- [ ] Deploy to GCP Cloud Run:
  ```bash
  gcloud run deploy execution-service \
    --source . \
    --region us-central1 \
    --allow-unauthenticated
  ```
- [ ] Set environment variables (MONGODB_URL, JWT_SECRET)
- [ ] Update MongoDB Atlas IP whitelist (allow Cloud Run IPs)
- [ ] Test deployed API

**Deliverable:** API URL (e.g., `https://execution-service-xyz.run.app`)

---

### 10.2 CI/CD Pipeline
**Goal:** Automated testing on every commit

**File:** `.github/workflows/test.yml`

```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest -v --cov=app
      - name: Lint
        run: uv run ruff check app/
```

**Tasks:**
- [ ] Create workflow file
- [ ] Test CI runs on push
- [ ] Add coverage reporting
- [ ] Add badge to README

---

## Phase 11: Polish & Documentation (Day 11-12)

### 11.1 API Documentation
**Goal:** Excellent developer experience

**Tasks:**
- [ ] Add docstrings to all endpoints
- [ ] Add request/response examples
- [ ] Test Swagger UI (`/docs`)
- [ ] Test ReDoc UI (`/redoc`)
- [ ] Update README with:
  - Quick start guide
  - API endpoint reference
  - Authentication guide
  - MCP integration guide

---

### 11.2 Testing & Bug Fixes
**Goal:** Production-ready quality

**Tasks:**
- [ ] Achieve >80% test coverage
- [ ] Manual testing of all endpoints
- [ ] Test with real execution system data
- [ ] Fix edge cases
- [ ] Error handling improvements
- [ ] Logging improvements

---

### 11.3 Security Hardening
**Goal:** Production-grade security

**Tasks:**
- [ ] Rate limiting (slowapi)
- [ ] CORS configuration
- [ ] Input validation (all endpoints)
- [ ] SQL/NoSQL injection prevention
- [ ] Secrets management (don't log tokens)
- [ ] HTTPS only in production
- [ ] Security headers

---

## Success Criteria

### MVP Complete When:
- [ ] MongoDB Atlas running
- [ ] All auth endpoints working (register, login)
- [ ] All project CRUD endpoints working
- [ ] All action CRUD endpoints working
- [ ] Time tracking working (start/stop timer, entries)
- [ ] Sync script working (bidirectional)
- [ ] execution-system-mcp calling API
- [ ] Deployed to GCP Cloud Run
- [ ] >80% test coverage
- [ ] Can use via Claude Code

### Phase 2 Ready When:
- iOS/Mac app can authenticate
- iOS/Mac app can start/stop timers
- iOS/Mac app can list projects
- Cross-device sync working

---

## Risk Mitigation

### Risk: Sync conflicts (file vs DB)
**Mitigation:**
- Last-write-wins initially
- Add conflict detection warnings
- User can choose resolution strategy

### Risk: MongoDB Atlas free tier limits
**Mitigation:**
- Monitor usage
- Optimize queries
- Upgrade if needed ($9/month M10)

### Risk: Deployment complexity
**Mitigation:**
- Use Cloud Run (serverless, simple)
- Start with manual deploys
- Add CI/CD later

### Risk: Breaking changes to MCP
**Mitigation:**
- Keep file-based fallback initially
- Gradual migration
- Version API endpoints

---

## Timeline Summary

| Phase | Days | Status |
|-------|------|--------|
| 1. Setup & Infrastructure | 1 | Complete |
| 2. Database & Models | 1 | Complete |
| 3. Authentication | 1 | In Progress |
| 4. Projects CRUD | 2 | Pending |
| 5. Actions CRUD | 1 | Pending |
| 6. Time Tracking | 1 | Pending |
| 7. Goals | 1 | Pending |
| 8. File Sync | 1 | Pending |
| 9. MCP Integration | 1 | Pending |
| 10. Deployment | 1 | Pending |
| 11. Polish | 1 | Pending |
| **Total** | **12 days** | |

**Estimated completion:** 2025-11-21 (working full-time)

---

## Next Steps

**Completed:**
- Phase 1: MongoDB Atlas setup and repository scaffolding
- Phase 2: Database models and utilities (48 tests passing)

**Right now (Phase 3):**
1. Implement AuthService (business logic)
2. Write auth endpoint tests
3. Implement auth router
4. Wire up in main.py
5. Manual testing with curl/httpx

**Ready to begin Phase 3 - Authentication!**
