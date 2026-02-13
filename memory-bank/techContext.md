# Tech Context

## Stack

- **Runtime:** Python 3.8+
- **Framework:** FastAPI
- **Database:** PostgreSQL (primary), SQLite (unit tests only)
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Vector DB:** Qdrant
- **Cache/Rate limit:** Redis (optional) or in-memory
- **AI:** ai-service microservice (HTTP); no direct LLM calls in api-service

## Development Setup

### Database

- **Use PostgreSQL in development** — SQLite causes type/syntax mismatches with production
- **Default:** `postgresql://confida_dev:dev_password@localhost:5432/confida_dev`
- **Docker option:** `docker-compose.dev.yml` with postgres:15
- **Migrations:** `alembic revision --autogenerate -m "..."` then `alembic upgrade head`
- **Seed:** `python seed_data.py` or `python run_seed.py`

See [docs/DEVELOPMENT_SETUP.md](../docs/DEVELOPMENT_SETUP.md), [docs/DATABASE_SETUP.md](../docs/DATABASE_SETUP.md).

### Key Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| DATABASE_URL | postgresql://confida_dev:... | DB connection |
| AI_SERVICE_URL | http://localhost:8001 | ai-service base URL |
| SECRET_KEY | (change in prod) | JWT signing |
| ENABLE_ADMIN_ROUTES | true | Admin endpoints |
| ENABLE_SECURITY_ROUTES | false | Security audit routes |
| RATE_LIMIT_BACKEND | memory | memory or redis |
| CACHE_BACKEND | memory | memory or redis |
| ASYNC_DATABASE_ENABLED | true | Async DB operations |
| TTS_PROVIDER | coqui | coqui, elevenlabs, playht |
| QDRANT_URL | http://localhost:6333 | Qdrant |

Full list: [docs/environment-variables.md](../docs/environment-variables.md).

### Running

```bash
uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000, Docs: http://localhost:8000/docs

## Testing

- **Framework:** pytest, pytest-cov, pytest-asyncio
- **Unit tests:** SQLite in-memory for speed
- **Integration tests:** PostgreSQL (match dev)
- **Structure:** `tests/unit/`, `tests/integration/`, `tests/e2e/`
- **Run:** `pytest`, `pytest tests/unit/`, `pytest tests/integration/`
- **Script:** `python scripts/run_tests.py --type all --coverage`
- **CI:** `scripts/run_ci_tests_locally.sh`

See [docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md).

## Deployment

- **Railway** — One-click, managed Postgres/Redis/Qdrant
- **Render** — Web service + managed DBs
- **Fly.io** — Global scale, CLI deploy
- **Cloud Run** — Google, pay-per-use

See [docs/README_DEPLOY.md](../docs/README_DEPLOY.md), [docs/PRODUCTION_DEPLOYMENT_GUIDE.md](../docs/PRODUCTION_DEPLOYMENT_GUIDE.md).

## Question Bank

- **Migration:** `python scripts/migrate_questions.py`
- **Seeding:** `python scripts/seed_question_bank.py` (from `data/sample_questions.json`)
- **Validation:** `python scripts/validate_migration.py`

See [docs/QUESTION_BANK_MIGRATION_GUIDE.md](../docs/QUESTION_BANK_MIGRATION_GUIDE.md).

## Vector Database

- **Qdrant** at QDRANT_URL
- **Collections:** questions, job descriptions, answers, user patterns
- **Init:** `POST /api/v1/vector/collections/initialize` (if endpoint exists)
- **Health:** `/health` includes vector_database status

See [docs/VECTOR_DATABASE_GUIDE.md](../docs/VECTOR_DATABASE_GUIDE.md).
