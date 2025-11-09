# Execution Service - Architecture

## Overview

The execution service is the backend for an AI-agent-first execution system that manages projects, actions, goals, and time tracking through natural conversation and APIs.

**Product Vision:** Users manage their execution system by talking to an AI agent (via MCP tools), using mobile apps, or eventually a custom GUI - all backed by this service.

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph "Clients"
        VSCode[VS Code + Claude Code]
        iOS[iOS/Mac Apps]
        GUI[Custom GUI<br/>Future]
    end

    subgraph "MCP Servers (Python)"
        ExecMCP[execution-system-mcp<br/>Projects, Actions, Goals]
        TimeMCP[time-tracking-mcp<br/>Timers, Entries, Reports]
        CalMCP[calendar-mcp<br/>Calendar Integration]
    end

    subgraph "Execution Service (This Repo)"
        API[FastAPI REST API]

        subgraph "Routers"
            AuthR["Auth Router<br/>/auth"]
            ProjR["Project Router<br/>/projects"]
            ActR["Action Router<br/>/actions"]
            TimeR["Time Router<br/>/timers, /entries, /reports"]
            GoalR["Goal Router<br/>/goals"]
        end

        subgraph "Services"
            ProjSvc[ProjectService]
            ActSvc[ActionService]
            TimeSvc[TimerService]
            SyncSvc[SyncService]
        end

        Sync[Bidirectional Sync<br/>Files ↔ MongoDB]
    end

    subgraph "Data Layer"
        MongoDB[(MongoDB Atlas<br/>Multi-tenant)]
        Files[Markdown Files<br/>Local System<br/>Temporary]
    end

    VSCode -->|MCP Protocol| ExecMCP
    VSCode -->|MCP Protocol| TimeMCP
    iOS -->|REST API| API
    GUI -->|REST API| API

    ExecMCP -->|HTTP| API
    TimeMCP -->|HTTP| API
    CalMCP -->|External API| Calendar

    API --> AuthR
    API --> ProjR
    API --> ActR
    API --> TimeR
    API --> GoalR

    ProjR --> ProjSvc
    ActR --> ActSvc
    TimeR --> TimeSvc

    ProjSvc --> MongoDB
    ActSvc --> MongoDB
    TimeSvc --> MongoDB

    Sync -.->|Reads/Writes| Files
    Sync -.->|Syncs| MongoDB

    style ExecMCP fill:#e3f2fd
    style TimeMCP fill:#e3f2fd
    style API fill:#fff3e0
    style MongoDB fill:#f3e5f5
    style Sync fill:#e8f5e9
```

---

## 2. Database Schema (Phase 1)

```mermaid
erDiagram
    USERS ||--o{ PROJECTS : owns
    USERS ||--o{ ACTIONS : owns
    USERS ||--o{ TIME_ENTRIES : owns
    USERS ||--o{ GOALS : owns

    PROJECTS ||--o{ TIME_ENTRIES : "tracks time"
    PROJECTS ||--o{ ACTIONS : "has actions"

    USERS {
        uuid _id PK
        string email UK
        string name
        string api_key UK
        timestamp created_at
        timestamp updated_at
    }

    PROJECTS {
        uuid _id PK
        uuid user_id FK
        string title
        string slug UK
        string area
        string folder "active | incubator | completed | descoped"
        string type "standard | coordination | habit | goal"
        date created
        date started
        date last_reviewed
        date completed
        date descoped
        date due
        text content "Full markdown body"
        boolean deleted "Soft delete flag"
        timestamp deleted_at "When deleted"
        object time_stats
        object sync
        timestamp created_at
        timestamp updated_at
    }

    ACTIONS {
        uuid _id PK
        uuid user_id FK
        string text "Action text - editable"
        string context "@laptop | @phone | @home | @errands | @waiting | @deferred | @incubating"
        string project "Optional project slug"
        date date "Creation date"
        date due "Due date"
        date defer "Defer until date"
        boolean completed
        timestamp completed_at
        boolean deleted "Soft delete flag"
        timestamp deleted_at "When deleted"
        object sync
        timestamp created_at
        timestamp updated_at
    }

    TIME_ENTRIES {
        uuid _id PK
        uuid user_id FK
        uuid project_id FK
        string project_title
        string description
        timestamp start_time
        timestamp end_time
        int duration_seconds
        float duration_hours
        timestamp created_at
        timestamp updated_at
    }

    GOALS {
        uuid _id PK
        uuid user_id FK
        string title
        string slug UK
        string area
        string folder
        string type
        date started
        string status
        text content
        array milestones
        object sync
        timestamp created_at
        timestamp updated_at
    }
```

**Key Design Decisions:**

1. **Multi-tenancy:** Every collection has `user_id` - all queries filtered by user
2. **Soft delete:** `deleted` boolean flag preserves audit trail, allows recovery
3. **Denormalization:** `project_title` in `time_entries` for display without joins
4. **Sync metadata:** `sync` object tracks file sync state (file_path, timestamps, hash)
5. **Flexible content:** `content` field stores markdown for flexibility - fully editable
6. **Time stats:** Denormalized on projects for fast dashboard queries

---

## 3. Sequence Diagram: Starting a Timer

```mermaid
sequenceDiagram
    actor User
    participant Claude as Claude Code
    participant MCP as time-tracking-mcp
    participant API as execution-service API
    participant DB as MongoDB

    User->>Claude: "Start timer on ml-refresh project"
    Claude->>MCP: start_timer(project_name="ml-refresh")

    MCP->>API: POST /api/timers/start
    Note over MCP,API: Body: {"project_name": "ml-refresh"}

    API->>DB: Find project by slug
    Note over API,DB: projects.find_one({"user_id": user_id, "slug": "ml-refresh"})

    alt Project not found
        DB-->>API: null
        API-->>MCP: 404 Error: Project not found
        MCP-->>Claude: Error message
        Claude-->>User: "Project 'ml-refresh' not found"
    else Project found
        DB-->>API: Project document

        API->>DB: Check for running timer
        Note over API,DB: time_entries.find_one({"user_id": user_id, "end_time": null})

        alt Timer already running
            DB-->>API: Running entry
            API-->>MCP: 400 Error: Timer already running
            MCP-->>Claude: Error message
            Claude-->>User: "Timer already running on [other project]"
        else No running timer
            DB-->>API: null

            API->>DB: Create time entry
            Note over API,DB: time_entries.insert_one({<br/>  user_id, project_id,<br/>  start_time: now(),<br/>  end_time: null<br/>})
            DB-->>API: entry_id

            API-->>MCP: 200 OK + entry details
            MCP-->>Claude: Success response
            Claude-->>User: "✓ Timer started on ml-refresh at 2:34 PM"
        end
    end
```

---

## 4. Sequence Diagram: Creating a Project

```mermaid
sequenceDiagram
    actor User
    participant Claude as Claude Code
    participant MCP as execution-system-mcp
    participant API as execution-service API
    participant DB as MongoDB

    User->>Claude: "Create project: Learn Rust in Learning area"
    Claude->>MCP: create_project(title="Learn Rust", area="learning", type="standard", folder="active")

    MCP->>API: POST /api/projects
    Note over MCP,API: Body: {title, area, type, folder, due}

    API->>API: Validate data<br/>Generate slug: "learn-rust"<br/>Set timestamps

    API->>DB: Check for duplicate slug
    Note over API,DB: projects.find_one({user_id, slug: "learn-rust"})

    alt Slug exists
        DB-->>API: Project found
        API-->>MCP: 409 Conflict: Project already exists
        MCP-->>Claude: Error message
        Claude-->>User: "Project 'Learn Rust' already exists"
    else Slug available
        DB-->>API: null

        API->>DB: Insert project document
        Note over API,DB: projects.insert_one({<br/>  user_id, title, slug,<br/>  area, folder, type,<br/>  created, started,<br/>  content: template<br/>})
        DB-->>API: project_id

        API-->>MCP: 201 Created + project data
        MCP-->>Claude: Success response
        Claude-->>User: "✓ Created project 'Learn Rust' in Learning area"

        Note over User,DB: Later, sync writes to file...
    end
```

---

## 5. Sequence Diagram: Adding an Action

```mermaid
sequenceDiagram
    actor User
    participant Claude as Claude Code
    participant MCP as execution-system-mcp
    participant API as execution-service API
    participant DB as MongoDB

    User->>Claude: "Add action: Review Rust book chapter 3 @laptop +learn-rust due:2025-11-15"
    Claude->>MCP: add_action(text, context="@laptop", project="learn-rust", due="2025-11-15")

    MCP->>API: POST /api/actions
    Note over MCP,API: Body: {text, context, project, due, defer}

    API->>API: Parse todo.txt format<br/>Validate context<br/>Set creation date

    alt Project specified
        API->>DB: Validate project exists
        Note over API,DB: projects.find_one({user_id, slug: "learn-rust"})

        alt Project not found
            DB-->>API: null
            API-->>MCP: 404 Error: Project not found
            MCP-->>Claude: Error message
            Claude-->>User: "Project 'learn-rust' not found"
        else Project found
            DB-->>API: Project document

            API->>DB: Insert action document
            Note over API,DB: actions.insert_one({<br/>  user_id, text,<br/>  context, project,<br/>  date, due,<br/>  completed: false<br/>})
            DB-->>API: action_id

            API-->>MCP: 201 Created + action data
            MCP-->>Claude: Success response
            Claude-->>User: "✓ Added action to @laptop"
        end
    else No project
        API->>DB: Insert action without project
        DB-->>API: action_id
        API-->>MCP: 201 Created
        MCP-->>Claude: Success
        Claude-->>User: "✓ Added action to @laptop"
    end
```

---

## 6. Sequence Diagram: Completing a Project

```mermaid
sequenceDiagram
    actor User
    participant Claude as Claude Code
    participant MCP as execution-system-mcp
    participant API as execution-service API
    participant DB as MongoDB

    User->>Claude: "Complete project: Learn Rust"
    Claude->>MCP: complete_project(title="Learn Rust")

    MCP->>API: POST /api/projects/learn-rust/complete

    API->>DB: Find project
    Note over API,DB: projects.find_one({user_id, slug: "learn-rust"})

    alt Project not found
        DB-->>API: null
        API-->>MCP: 404 Error: Project not found
        MCP-->>Claude: Error message
        Claude-->>User: "Project not found"
    else Project found
        DB-->>API: Project document

        API->>DB: Check for incomplete actions
        Note over API,DB: actions.count_documents({<br/>  user_id,<br/>  project: "learn-rust",<br/>  completed: false<br/>})

        alt Has incomplete actions
            DB-->>API: count > 0
            API-->>MCP: 400 Error: Project has incomplete actions
            MCP-->>Claude: Error message
            Claude-->>User: "Cannot complete: Project has 3 incomplete actions"
        else No incomplete actions
            DB-->>API: count = 0

            API->>DB: Update project
            Note over API,DB: projects.update_one({<br/>  _id: project_id<br/>}, {<br/>  $set: {<br/>    folder: "completed",<br/>    completed: ISODate(),<br/>    updated_at: ISODate()<br/>  }<br/>})
            DB-->>API: Success

            API-->>MCP: 200 OK + updated project
            MCP-->>Claude: Success response
            Claude-->>User: "✓ Completed project 'Learn Rust'"

            Note over API,DB: Sync will move file to completed/ folder
        end
    end
```

---

## 7. Sequence Diagram: Listing Projects with Filtering

```mermaid
sequenceDiagram
    actor User
    participant Claude as Claude Code
    participant MCP as execution-system-mcp
    participant API as execution-service API
    participant DB as MongoDB

    User->>Claude: "Show me active projects in Career area"
    Claude->>MCP: list_projects(folder="active", filter_area="career")

    MCP->>API: GET /api/projects?folder=active&area=career

    API->>API: Parse query params<br/>Build MongoDB query

    API->>DB: Query projects
    Note over API,DB: projects.find({<br/>  user_id: user_id,<br/>  folder: "active",<br/>  area: "career"<br/>}).sort("last_reviewed", -1)

    DB-->>API: Array of project documents

    API->>API: Group by area<br/>Format response<br/>Add metadata

    API-->>MCP: 200 OK + JSON response
    Note over API,MCP: {<br/>  "groups": {<br/>    "Career": [<br/>      {title, slug, due, ...}<br/>    ]<br/>  },<br/>  "total": 5<br/>}

    MCP-->>Claude: Formatted data
    Claude-->>User: "Active Career Projects:<br/>- DE Shaw TPM Role (due 2025-11-15)<br/>- Resume Update<br/>- LinkedIn Optimization<br/>..."
```

---

## 8. Sequence Diagram: Editing a Project

```mermaid
sequenceDiagram
    actor User
    participant Claude as Claude Code
    participant MCP as execution-system-mcp
    participant API as execution-service API
    participant DB as MongoDB

    User->>Claude: "Update the DE Shaw project - add notes from call with Shariff"
    Claude->>MCP: update_project(slug="de-shaw-technical-product-manager", content="# DE Shaw TPM\n\n## Context\n\nShariff called today...", title, area, due)

    MCP->>API: PATCH /api/projects/de-shaw-technical-product-manager
    Note over MCP,API: Body: {<br/>  content: "updated markdown",<br/>  title: "Updated Title" (optional),<br/>  area: "career" (optional),<br/>  due: "2025-11-20" (optional)<br/>}

    API->>DB: Find project
    Note over API,DB: projects.find_one({<br/>  user_id,<br/>  slug: "de-shaw-technical-product-manager",<br/>  deleted: false<br/>})

    alt Project not found
        DB-->>API: null
        API-->>MCP: 404 Error: Project not found
        MCP-->>Claude: Error message
        Claude-->>User: "Project not found"
    else Project found
        DB-->>API: Project document

        API->>API: Validate changes<br/>Check if slug needs regeneration<br/>Set updated_at timestamp

        alt Title changed
            API->>API: Generate new slug from title
            API->>DB: Check new slug doesn't conflict
            Note over API,DB: projects.find_one({user_id, slug: new_slug})

            alt Slug conflict
                DB-->>API: Existing project
                API-->>MCP: 409 Conflict: Slug already exists
                MCP-->>Claude: Error message
                Claude-->>User: "A project with that title already exists"
            end
        end

        API->>DB: Update project
        Note over API,DB: projects.update_one({<br/>  _id: project_id<br/>}, {<br/>  $set: {<br/>    content: new_content,<br/>    title: new_title,<br/>    area: new_area,<br/>    due: new_due,<br/>    slug: new_slug (if changed),<br/>    updated_at: ISODate()<br/>  }<br/>})
        DB-->>API: Success

        API-->>MCP: 200 OK + updated project data
        MCP-->>Claude: Success response
        Claude-->>User: "✓ Updated project 'DE Shaw TPM'"

        Note over API,DB: Sync will update file with new content
    end
```

---

## 9. Sequence Diagram: Deleting a Project (Soft Delete)

```mermaid
sequenceDiagram
    actor User
    participant Claude as Claude Code
    participant MCP as execution-system-mcp
    participant API as execution-service API
    participant DB as MongoDB

    User->>Claude: "Delete the old website redesign project"
    Claude->>MCP: delete_project(slug="website-redesign")

    MCP->>API: DELETE /api/projects/website-redesign

    API->>DB: Find project
    Note over API,DB: projects.find_one({<br/>  user_id,<br/>  slug: "website-redesign",<br/>  deleted: false<br/>})

    alt Project not found
        DB-->>API: null
        API-->>MCP: 404 Error: Project not found
        MCP-->>Claude: Error message
        Claude-->>User: "Project not found"
    else Project found
        DB-->>API: Project document

        API->>DB: Soft delete project
        Note over API,DB: projects.update_one({<br/>  _id: project_id<br/>}, {<br/>  $set: {<br/>    deleted: true,<br/>    deleted_at: ISODate(),<br/>    updated_at: ISODate()<br/>  }<br/>})
        DB-->>API: Success

        API->>DB: Soft delete associated actions
        Note over API,DB: actions.update_many({<br/>  user_id,<br/>  project: "website-redesign",<br/>  completed: false<br/>}, {<br/>  $set: {<br/>    deleted: true,<br/>    deleted_at: ISODate()<br/>  }<br/>})
        DB-->>API: Success

        API-->>MCP: 200 OK
        MCP-->>Claude: Success response
        Claude-->>User: "✓ Deleted project 'Website Redesign' and 5 associated actions"

        Note over API,DB: Sync will delete file (or move to .trash/)
    end
```

---

## 10. Sequence Diagram: Bidirectional Sync

```mermaid
sequenceDiagram
    participant Sync as Sync Script
    participant FS as File System
    participant API as execution-service API
    participant DB as MongoDB

    Note over Sync: Sync triggered (manual/scheduled/file watch)

    loop For each project file
        Sync->>FS: Get file mtime & hash
        FS-->>Sync: mtime, hash

        Sync->>API: GET /api/projects/{slug}/sync_status
        API->>DB: Find project sync metadata
        DB-->>API: sync {file_updated_at, db_updated_at, file_hash}
        API-->>Sync: Sync metadata

        alt File newer (mtime > db_updated_at)
            Sync->>FS: Read file content
            FS-->>Sync: YAML + Markdown

            Sync->>API: PUT /api/projects/{slug}
            Note over Sync,API: Body: parsed project data + new file_hash
            API->>DB: Update project document
            DB-->>API: Success
            API-->>Sync: 200 OK

            Note over Sync: File → MongoDB (File wins)

        else DB newer (db_updated_at > file mtime)
            Sync->>API: GET /api/projects/{slug}
            API->>DB: Find project
            DB-->>API: Project document
            API-->>Sync: Project data

            Sync->>FS: Write markdown file
            FS-->>Sync: Success

            Note over Sync: MongoDB → File (DB wins)

        else Hash matches (no changes)
            Note over Sync: Skip - already in sync
        end
    end

    Note over Sync: Sync complete
```

---

## 11. API Endpoint Structure

```mermaid
graph TB
    subgraph "Authentication"
        Auth["POST /auth/register<br/>POST /auth/login<br/>GET /auth/me"]
    end

    subgraph "Projects (10k)"
        ProjList["GET /projects<br/>filter: folder, area"]
        ProjCreate["POST /projects"]
        ProjGet["GET /projects/:slug"]
        ProjUpdate["PATCH /projects/:slug"]
        ProjDelete["DELETE /projects/:slug"]
        ProjComplete["POST /projects/:slug/complete"]
        ProjSync["GET /projects/:slug/sync_status"]
    end

    subgraph "Actions (00k)"
        ActList["GET /actions<br/>filter: context, completed"]
        ActCreate["POST /actions"]
        ActUpdate["PATCH /actions/:id"]
        ActComplete["POST /actions/:id/complete"]
    end

    subgraph "Time Tracking"
        TimerStart["POST /timers/start"]
        TimerStop["POST /timers/stop"]
        TimerCurrent["GET /timers/current"]
        EntryList["GET /entries<br/>filter: date range"]
        EntryCreate["POST /entries"]
        EntryUpdate["PATCH /entries/:id"]
        ReportSummary["GET /reports/summary<br/>filter: date range"]
    end

    subgraph "Goals (30k)"
        GoalList["GET /goals"]
        GoalCreate["POST /goals"]
        GoalUpdate["PATCH /goals/:slug"]
    end

    style Auth fill:#fbbf24
    style ProjList fill:#60a5fa
    style ActList fill:#34d399
    style TimerStart fill:#f87171
    style GoalList fill:#a78bfa
```

**Authentication:**
- JWT tokens for MCP/API auth
- API keys for persistent auth (mobile apps)

**Common patterns:**
- All endpoints scoped to `user_id` from auth token
- Use slugs for human-readable URLs (projects, goals)
- Use UUIDs for actions, time entries
- Query parameters for filtering/pagination
- Soft delete pattern: `deleted` flag, all queries filter `deleted: false` by default

### PATCH Endpoint Details (Content Editing)

**PATCH /api/projects/:slug**
```json
{
  "content": "# Updated Project\n\n## New Context\nDetailed notes here...",
  "title": "Updated Title",  // Optional - regenerates slug if changed
  "area": "career",           // Optional
  "due": "2025-11-20",        // Optional - ISO date or null to remove
  "folder": "active"          // Optional - active | incubator | completed | descoped
}
```
- Partial updates supported (only send fields to change)
- `content` field stores full markdown body - completely editable
- Changing `title` regenerates slug (checks for conflicts)
- Returns 409 Conflict if new slug already exists
- Returns 404 if project not found or deleted

**PATCH /api/actions/:id**
```json
{
  "text": "Updated action text",
  "due": "2025-11-20",        // Optional - ISO date or null to remove
  "defer": "2025-11-15",      // Optional - ISO date or null to remove
  "context": "@phone",        // Optional - change context
  "project": "new-project"    // Optional - change project (validates existence)
}
```
- Partial updates supported
- `text` field is completely editable
- Changing `project` validates new project exists
- Returns 404 if project not found or action deleted

### DELETE Endpoint Details (Soft Delete)

**DELETE /api/projects/:slug**
- Sets `deleted: true`, `deleted_at: timestamp`
- Also soft deletes all associated incomplete actions
- Returns count of deleted actions
- Does NOT physically remove from database (audit trail preserved)
- Sync script deletes file (or moves to `.trash/`)

**DELETE /api/actions/:id**
- Sets `deleted: true`, `deleted_at: timestamp`
- Does NOT physically remove from database

**Recovering Deleted Items:**
```
POST /api/projects/:slug/restore
POST /api/actions/:id/restore
```
- Sets `deleted: false`, clears `deleted_at`
- Only available within 30 days (configurable)

---

## 12. Component Diagram

```mermaid
graph TB
    subgraph "execution-service/"
        Main[app/main.py<br/>FastAPI App]

        subgraph "Routers"
            AuthRouter[routers/auth.py]
            ProjRouter[routers/projects.py]
            ActRouter[routers/actions.py]
            TimeRouter[routers/timers.py]
        end

        subgraph "Services (Business Logic)"
            AuthSvc[services/auth_service.py<br/>JWT, API keys]
            ProjSvc[services/project_service.py<br/>CRUD, validation]
            ActSvc[services/action_service.py<br/>Todo.txt parsing]
            TimeSvc[services/timer_service.py<br/>Start/stop, duration calc]
            SyncSvc[services/sync_service.py<br/>Conflict resolution]
        end

        subgraph "Models (Pydantic)"
            UserModel[models/user.py]
            ProjModel[models/project.py]
            ActModel[models/action.py]
            TimeModel[models/time_entry.py]
        end

        subgraph "Database"
            DBConn[database.py<br/>MongoDB connection]
            Collections[Collections:<br/>users, projects,<br/>actions, time_entries]
        end

        subgraph "Sync Tool"
            SyncScript[sync/sync_engine.py]
            FileReader[sync/file_reader.py<br/>Parse markdown+YAML]
            FileWriter[sync/file_writer.py<br/>Write markdown+YAML]
        end

        Config[config.py<br/>Settings, env vars]
        Dependencies[dependencies.py<br/>Auth, DB injection]
    end

    Main --> AuthRouter
    Main --> ProjRouter
    Main --> ActRouter
    Main --> TimeRouter

    AuthRouter --> AuthSvc
    ProjRouter --> ProjSvc
    ActRouter --> ActSvc
    TimeRouter --> TimeSvc

    AuthSvc --> DBConn
    ProjSvc --> DBConn
    ActSvc --> DBConn
    TimeSvc --> DBConn

    SyncScript --> FileReader
    SyncScript --> FileWriter
    SyncScript --> ProjSvc
    SyncScript --> ActSvc

    DBConn --> Collections

    style Main fill:#ff2d20
    style AuthSvc fill:#4f46e5
    style SyncScript fill:#10b981
    style DBConn fill:#8b5cf6
```

---

## 13. Use Case Diagram

```mermaid
graph TB
    subgraph "Actors"
        User[User<br/>Brian]
        David[User<br/>David]
        Agent[AI Agent<br/>Future]
        Sync[Sync Script<br/>Background]
    end

    subgraph "Project Management (10k)"
        UC1[Create Project]
        UC2[List Active Projects]
        UC3[Update Project]
        UC4[Complete Project]
        UC5[Review Projects]
    end

    subgraph "Action Management (00k)"
        UC6[Add Next Action]
        UC7[List Actions by Context]
        UC8[Complete Action]
        UC9[Move to Waiting]
    end

    subgraph "Time Tracking"
        UC10[Start Timer]
        UC11[Stop Timer]
        UC12[View Current Timer]
        UC13[Add Manual Entry]
        UC14[Weekly Summary]
    end

    subgraph "Sync Operations"
        UC15[Sync Files to DB]
        UC16[Sync DB to Files]
        UC17[Resolve Conflicts]
    end

    subgraph "Multi-Tenant"
        UC18[User Registration]
        UC19[User Login]
        UC20[API Key Auth]
    end

    User --> UC1
    User --> UC2
    User --> UC6
    User --> UC7
    User --> UC10
    User --> UC11
    User --> UC14

    David --> UC1
    David --> UC2
    David --> UC6
    David --> UC10

    Agent --> UC1
    Agent --> UC2
    Agent --> UC10

    Sync --> UC15
    Sync --> UC16
    Sync --> UC17

    User --> UC18
    User --> UC19
    User --> UC20

    style User fill:#e3f2fd
    style David fill:#e3f2fd
    style Agent fill:#fff3e0
    style Sync fill:#e8f5e9
```

---

## 14. Technology Stack

### Backend
- **Framework:** FastAPI (Python 3.11+)
- **Database:** MongoDB Atlas (cloud)
- **ODM:** Motor (async MongoDB client) + Pydantic
- **Auth:** python-jose (JWT), passlib (password hashing)
- **Testing:** pytest, pytest-asyncio, httpx
- **Deployment:** GCP Cloud Run (containerized)

### Sync Tool
- **File Parsing:** PyYAML, python-frontmatter
- **File Watching:** watchdog (optional)
- **Conflict Resolution:** Timestamp-based (last write wins)

### Development
- **Package Manager:** uv (fast Python package manager)
- **Type Checking:** Pydantic models + Python type hints
- **Code Quality:** ruff (linting), black (formatting)
- **TDD:** pytest with high coverage

---

## 15. Deployment Architecture

```mermaid
graph TB
    subgraph "User Devices"
        Mac[Mac + VS Code]
        iPhone[iPhone App]
    end

    subgraph "GCP Cloud Run"
        API[execution-service<br/>FastAPI Container]
    end

    subgraph "MongoDB Atlas (Cloud)"
        Cluster[MongoDB Cluster<br/>Multi-tenant DB]
    end

    subgraph "Local (User's Machine)"
        Files[Markdown Files]
        SyncLocal[Sync Script<br/>Runs locally]
    end

    Mac -->|HTTPS| API
    iPhone -->|HTTPS| API

    API -->|MongoDB Protocol| Cluster

    SyncLocal -.->|Reads/Writes| Files
    SyncLocal -->|HTTPS| API

    style API fill:#ff2d20
    style Cluster fill:#8b5cf6
    style SyncLocal fill:#10b981
```

**Key Points:**
- API hosted on GCP Cloud Run (auto-scaling, serverless)
- MongoDB Atlas (managed, multi-region)
- Sync script runs locally on user's machine (access to files)
- Mobile apps call API directly
- MCP servers call API from local Claude Code

---

## 16. Summary: All Supported Operations

**Project Operations (10k):**
- create_project, list_projects, complete_project, activate_project
- **edit_project** (update content, title, metadata), **delete_project** (soft delete)
- move_to_incubator, descope_project, update_due_date, update_area, update_type
- search_projects, audit_projects, list_needing_review

**Action Operations (00k):**
- add_action, add_to_waiting, add_to_deferred, add_to_incubating
- complete_action, **edit_action** (update text, metadata), **delete_action** (soft delete)
- list_actions, search_actions
- audit_actions, list_needing_review

**Time Tracking:**
- start_timer, stop_timer, get_current_timer
- add_entry, list_entries, update_entry
- get_weekly_summary, get_daily_breakdown

**Goal Operations (30k):**
- create_goal, list_goals, update_goal

**System Operations:**
- list_areas, update_review_dates
- sync_status, trigger_sync

All operations are:
- Multi-tenant (user_id scoped)
- Authenticated (JWT/API key)
- Validated (input checking, business rules)
- Synced (bidirectional file ↔ database)

---

## 17. Removed: Data Flow Creating a Project

*This diagram was replaced by Sequence Diagram #4 which covers the same flow in more detail.*

---

```mermaid
sequenceDiagram
    actor User
    participant Claude
    participant MCP
    participant API
    participant DB
    participant Sync

    User->>Claude: "Create project: Learn Rust"
    Claude->>MCP: create_project(title="Learn Rust", area="learning")

    MCP->>API: POST /api/projects
    Note over MCP,API: Body: {title, area, type, folder}

    API->>API: Validate data<br/>Generate slug<br/>Set timestamps

    API->>DB: Insert project document
    DB-->>API: project_id

    API->>DB: Update user's project count (optional)

    API-->>MCP: 201 Created + project data
    MCP-->>Claude: Success response
    Claude-->>User: "✓ Created project 'Learn Rust' in Learning area"

    Note over Sync: Later, sync runs...
    Sync->>API: GET /api/projects/learn-rust
    API->>DB: Find project
    DB-->>API: Project document
    API-->>Sync: Project data

    Sync->>Sync: Convert to markdown
    Note over Sync: Generate YAML frontmatter<br/>+ markdown body

    Sync->>Sync: Write file
    Note over Sync: File: 10k-projects/active/learning/learn-rust.md
```

---

## Phase 1 Scope (This Week)

**Build:**
1. FastAPI app structure
2. MongoDB connection + collections
3. User auth (JWT + API keys)
4. Projects CRUD API
5. Actions CRUD API
6. Time tracking API (start/stop timer, entries, summary)
7. Basic sync script (one-way: files → MongoDB)

**Testing:**
- Unit tests for services
- Integration tests for API endpoints
- Test with your personal data

**Deploy:**
- Local development first
- Deploy to GCP Cloud Run once working

---

*Last Updated: 2025-11-09*
