# Execution Service

Backend API for GTD execution system with MongoDB Atlas.

## Setup

### 1. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 2. Run Tests

```bash
pytest
```

### 3. Start Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Test API

Visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

## Project Structure

```
execution-service/
├── .env                    # Environment variables (gitignored)
├── .env.example           # Example environment variables
├── pyproject.toml         # Dependencies
├── app/
│   ├── main.py           # FastAPI app entry point
│   ├── config.py         # Settings from environment
│   ├── database.py       # MongoDB connection
│   ├── models/           # Pydantic models
│   ├── routers/          # API endpoints
│   └── services/         # Business logic
└── tests/                # Test suite
```

## MongoDB Atlas

Connection string is configured in `.env` file (never committed to git).

Database: `execution_system`
Collections: `users`, `projects`, `actions`, `time_entries`, `goals`

## Development

This project uses:
- **FastAPI** - Modern async web framework
- **Motor** - Async MongoDB driver
- **Pydantic** - Data validation
- **pytest** - Testing framework
- **pyenv + virtualenv** - Python environment management
