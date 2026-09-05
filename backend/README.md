# Orbis Video Studio AI - Backend Foundation

Backend core framework and relational domain database foundation.

## Technology Stack

- **Python**: 3.11+ / 3.12
- **Framework**: FastAPI
- **ORM**: SQLAlchemy 2.x
- **Migrations**: Alembic
- **Database**: PostgreSQL 16
- **Validation**: Pydantic / Pydantic-Settings
- **Test Runner**: pytest

## Developer Quick Start

### Local Development Setup

1. **Install Dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Run Tests:**
   ```bash
   pytest
   ```

3. **Database Migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Start Application Server:**
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Docker Compose Setup

Run backend and PostgreSQL database in containerized developer environment:

```bash
docker compose up --build
```

Health endpoints will be available at:
- `http://localhost:8000/health`
- `http://localhost:8000/api/v1/health`
