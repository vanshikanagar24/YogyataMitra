# YogyataMitra (योग्यता मित्र)

> **Explainable, Deterministic GovTech Welfare Entitlement Platform**

YogyataMitra helps Indian citizens determine their eligibility for government welfare schemes, understand why they qualify or do not qualify, identify required evidence, and navigate state-based verification workflows.

---

## 1. Project Purpose

YogyataMitra addresses the information asymmetry and opacity citizens face when navigating government entitlements:
- **Which schemes do I qualify for?**
- **Why do I qualify (or why am I excluded)?**
- **What information is missing?**
- **What documents / evidence must be submitted?**
- **What is the next actionable step in my journey?**

The platform operates on a **deterministic Rule AST engine** (final eligibility is strictly rule-based, never dictated by AI hallucinations), an **independent evidence verification model**, and an **explainable bilingual (English + Hindi) interface**.

---

## 2. Phase 1 Architecture & Technology Stack

Phase 1 establishes the repository infrastructure, containerized database, and FastAPI asynchronous foundation.

```
D:\YogyataMitra\
├── backend\
│   ├── app\
│   │   ├── api\          # Versioned API routes (Phase 6+)
│   │   ├── core\         # Settings, database session, async engine
│   │   ├── engine\       # Deterministic Rule AST engine (Phase 3+)
│   │   ├── models\       # SQLAlchemy 2.x Declarative Base & ORM models (Phase 2+)
│   │   ├── schemas\      # Pydantic v2 validation models
│   │   ├── services\     # Application & orchestration services
│   │   └── ai\           # Assistive AI services (bounded, non-decision-making)
│   ├── tests\            # Pytest test suite (health, config, integration)
│   ├── alembic\          # Alembic asynchronous migrations
│   │   └── versions\     # Migration scripts
│   ├── requirements.txt  # Pinned backend dependencies
│   ├── pytest.ini        # Pytest configuration
│   └── alembic.ini       # Alembic migration configuration
├── schemes_data\         # Declarative policy manifests & versioned Rule ASTs
├── docs\                 # System architecture and statutory policy documentation
├── docker-compose.yml    # PostgreSQL 16 container definition with healthcheck
├── .env.example          # Environment variable template
├── .env                  # Local environment configuration
├── .gitignore            # Git exclusion rules
└── README.md             # Project documentation
```

### Approved Stack:
- **Language**: Python 3.12+ (tested on Python 3.14.2)
- **Framework**: FastAPI (asynchronous, OpenAPI-documented)
- **Validation**: Pydantic v2 (`pydantic-settings`)
- **Database Engine**: PostgreSQL 16 (via Docker Compose)
- **ORM / Driver**: SQLAlchemy 2.x (async) + `asyncpg`
- **Migrations**: Alembic (async PostgreSQL support)
- **Testing**: Pytest + `pytest-asyncio` + HTTPX

---

## 3. Prerequisites

- **Python**: Version 3.12 or higher.
- **Docker Desktop**: Required to run containerized PostgreSQL 16.
- **Node.js**: Version 20+ (for Next.js frontend in Phase 8).
- **PowerShell**: Recommended for Windows terminal commands.

---

## 4. Environment Setup

The root configuration file `.env` controls environment variables across the backend and Docker containers.

1. **Clone or navigate to the workspace**:
   ```powershell
   cd D:\YogyataMitra
   ```

2. **Verify or copy the environment configuration**:
   ```powershell
   if (-not (Test-Path .env)) {
       Copy-Item .env.example .env
   }
   ```

3. **Core Environment Variables (`.env`)**:
   ```ini
   PROJECT_NAME=YogyataMitra
   ENVIRONMENT=development
   API_V1_STR=/api/v1

   POSTGRES_USER=yogyata_admin
   POSTGRES_PASSWORD=yogyata_secure_dev_pass
   POSTGRES_SERVER=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=yogyatamitra_db

   DATABASE_URL_OVERRIDE=
   ```

---

## 5. PostgreSQL via Docker Compose

PostgreSQL 16 runs in an isolated container with persistent storage and healthcheck monitoring.

1. **Start the database container**:
   ```powershell
   cd D:\YogyataMitra
   docker compose up -d
   ```

2. **Verify container status and healthcheck**:
   ```powershell
   docker compose ps
   ```
   *Expected output: `yogyatamitra_postgres ... Up (healthy) ... 0.0.0.0:5432->5432/tcp`*

3. **View database logs**:
   ```powershell
   docker compose logs -f postgres
   ```

4. **Stop the database container**:
   ```powershell
   docker compose down
   ```

> *Note for Windows environments with native PostgreSQL installed*: If port `5432` is already occupied by a local Windows PostgreSQL service, change `POSTGRES_PORT=5433` in `.env` and `docker-compose.yml`.

---

## 6. Backend Virtual Environment & Dependencies

1. **Navigate to the backend directory**:
   ```powershell
   cd D:\YogyataMitra\backend
   ```

2. **Create a virtual environment (if not already created)**:
   ```powershell
   python -m venv .venv
   ```

3. **Activate the virtual environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. **Install pinned dependencies**:
   ```powershell
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 7. Running the FastAPI Application

1. **Ensure the virtual environment is active**:
   ```powershell
   cd D:\YogyataMitra\backend
   .\.venv\Scripts\Activate.ps1
   ```

2. **Launch the development server**:
   ```powershell
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

3. **Verify endpoints in your browser or curl**:
   - **General Health Check**: `http://127.0.0.1:8000/health`
     ```json
     {"status": "ok", "service": "YogyataMitra"}
     ```
   - **Database Health Check**: `http://127.0.0.1:8000/health/db`
     ```json
     {"status": "ok", "database": "connected", "service": "YogyataMitra"}
     ```
   - **Interactive API Documentation (Swagger)**: `http://127.0.0.1:8000/docs`

---

## 8. Alembic Migrations

Alembic is configured to use asynchronous SQLAlchemy with `app.models.base.Base` metadata.

1. **Verify Alembic configuration**:
   ```powershell
   cd D:\YogyataMitra\backend
   alembic current
   ```

2. **Create a new migration revision (Phase 2+)**:
   ```powershell
   alembic revision --autogenerate -m "create_initial_models"
   ```

3. **Apply migrations**:
   ```powershell
   alembic upgrade head
   ```

---

## 9. Running Automated Tests

The test suite validates application startup, configuration loading, API contracts, and database connectivity.

1. **Run all standard tests**:
   ```powershell
   cd D:\YogyataMitra\backend
   python -m pytest -v
   ```

2. **Run integration tests (live PostgreSQL required)**:
   ```powershell
   python -m pytest -v -m integration
   ```

3. **Run non-integration tests only**:
   ```powershell
   python -m pytest -v -m "not integration"
   ```

---

## 10. Phase Development Roadmap

- **[x] Phase 0**: Architecture + official policy-source verification + scheme manifests.
- **[x] Phase 1**: Repository + environment + Docker PostgreSQL + FastAPI foundation.
- **[ ] Phase 2**: SQLAlchemy domain models + Alembic migrations.
- **[ ] Phase 3**: Rule AST + deterministic eligibility engine.
- **[ ] Phase 4**: Explainability + evaluation trace + audit trail.
- **[ ] Phase 5**: PM-KISAN + SSY policy datasets + comprehensive tests.
- **[ ] Phase 6**: Versioned FastAPI APIs.
- **[ ] Phase 7**: Citizen journey + state machine + evidence/verification.
- **[ ] Phase 8**: Next.js frontend.
- **[ ] Phase 9**: English/Hindi i18n + UX polish.
- **[ ] Phase 10**: Integration + E2E + final verification.
