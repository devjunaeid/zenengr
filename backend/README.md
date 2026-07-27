# ZenEngr Backend

FastAPI + PostgreSQL backend for the ZenEngr platform.

## Quick start (Docker)

```bash
# From repo root
docker compose --profile dev up -d postgres redis backend-dev

# Run migrations
docker compose --profile dev exec backend-dev uv run alembic upgrade head

# Seed dev data
docker compose --profile dev exec backend-dev uv run python -m scripts.seed_dev

# Run tests
docker compose --profile dev exec backend-dev uv run pytest -q

# Lint + type check
docker compose --profile dev exec backend-dev uv run ruff check .
docker compose --profile dev exec backend-dev uv run ruff format --check .
docker compose --profile dev exec backend-dev uv run mypy app
```

## Manual test

```bash
# Login as demo tenant admin
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"demo@demo-agency.dev","password":"changeme123!"}'

# Use returned token for /me
TOKEN="<access_token from above>"
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

## Config

Key env vars (supplied via `docker-compose.yml` and `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://app:app@postgres:5432/app` | Postgres connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `JWT_SECRET` | `change-me` | HMAC secret for JWT signing |
| `ENVIRONMENT` | `local` | Runtime environment |
| `CORS_ORIGINS` | `http://localhost:5173` | CORS allowlist |
| `SEED_SUPERADMIN_EMAIL` | `admin@zenengr.dev` | Seed super admin email |
| `SEED_SUPERADMIN_PASSWORD` | `changeme123!` | Seed super admin password |
| `SEED_DEMO_EMAIL` | `demo@demo-agency.dev` | Seed tenant admin email |
| `SEED_DEMO_PASSWORD` | `changeme123!` | Seed tenant admin password |

## Project structure

```
app/
  main.py             # FastAPI app factory
  api/v1/             # Route modules (thin controllers)
  services/           # Business logic
  repositories/       # SQLAlchemy data access
  models/             # ORM models
  schemas/            # Pydantic request/response
  core/               # Config, security, dependencies, errors
  db/                 # Engine, session, base
  utils/              # Pure helpers
scripts/              # Dev utilities (seed)
tests/                # Pytest tests
```
