# ZenEngr

> **Multi-Tenant Engineering Management & Client Collaboration Platform**
> Built with FastAPI, SvelteKit, Neon PostgreSQL, and a unified caching & automated CI/CD architecture.

---

## 🚀 Architecture Overview

ZenEngr is structured as a decoupled monorepo:

* **Backend (`backend/`)**: High-performance asynchronous REST API powered by **FastAPI**, **SQLAlchemy 2.0** (async), **Alembic**, and **Cashews** (in-memory + Redis toggleable caching).
* **Frontend (`frontend/`)**: Modern reactive web application powered by **SvelteKit 2**, **Svelte 5 Runes**, **Tailwind CSS v4**, and **Bits UI**.
* **Database**: **PostgreSQL 16** (Local Docker) / **Neon Serverless PostgreSQL** (Cloud/Production with SSL & connection pooling).
* **Infrastructure & CI/CD**: Containerized local development via **Docker Compose**, automated zero-downtime deployment via **GitHub Actions**.

```
zenengr/
├── frontend/                 # SvelteKit 2 SPA client portal & admin dashboard
├── backend/                  # FastAPI async REST API & Alembic migrations
├── docker-compose.yml        # Local dev stack (Postgres, Redis, MailHog, pgAdmin)
├── passenger_wsgi.py         # Production entry bridge for cPanel / CloudLinux
└── .github/workflows/
    └── deploy.yml            # Automated CI/CD pipeline (SSH / FTPS)
```

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.11+) |
| **ORM & Database Driver** | [SQLAlchemy 2.0 Async](https://docs.sqlalchemy.org/) + [asyncpg](https://github.com/MagicStack/asyncpg) |
| **Database** | [PostgreSQL 16](https://www.postgresql.org/) / [Neon](https://neon.tech/) |
| **Caching Layer** | [Cashews](https://github.com/Krukov/cashews) (`memory` in RAM or `redis` distributed) |
| **Frontend Framework** | [SvelteKit 2](https://kit.svelte.dev/) + [Svelte 5](https://svelte.dev/) (Runes) |
| **Styling & UI** | [Tailwind CSS v4](https://tailwindcss.com/) + [Bits UI](https://bits-ui.com/) |
| **Package Managers** | [uv](https://github.com/astral-sh/uv) (Python) + [npm](https://npmjs.com/) (Node.js) |
| **Process Management** | Phusion Passenger (cPanel) / Uvicorn (Docker/VPS) |

---

## ⚡ Quick Start (Local Development)

### 1. Prerequisites
* [Docker & Docker Compose](https://www.docker.com/) (or OrbStack)
* [Node.js 22+](https://nodejs.org/)
* [Python 3.11+ / uv](https://github.com/astral-sh/uv)

### 2. Environment Setup
ZenEngr uses an isolated 3-tier environment structure:

```bash
# 1. Setup root infrastructure env (Docker Compose)
cp .env.example .env

# 2. Setup backend API env
cp backend/.env.example backend/.env

# 3. Setup frontend client env
cp frontend/.env.example frontend/.env
```

### 3. Launch Local Dev Stack (One Command)
Start the complete containerized development environment with live hot-reloading:

```bash
docker compose --profile dev up
```

Once running:
* **Frontend Web App**: [`http://localhost:5173`](http://localhost:5173)
* **Backend REST API**: [`http://localhost:8000`](http://localhost:8000)
* **Interactive API Docs (Swagger)**: [`http://localhost:8000/docs`](http://localhost:8000/docs)
* **MailHog (Email Sandbox)**: [`http://localhost:8025`](http://localhost:8025)
* **pgAdmin (Database Manager)**: [`http://localhost:5050`](http://localhost:5050)

---

## 🧪 Testing & Code Quality

Run targeted checks directly or inside the running containers:

### Backend (Python / uv / pytest)
```bash
# Run backend test suite
docker exec zenengr-backend-dev-1 uv run pytest

# Check syntax and linting
docker exec zenengr-backend-dev-1 uv run ruff check .

# Database connection inspector
docker exec zenengr-backend-dev-1 uv run db-check
```

### Frontend (SvelteKit / ESLint / Prettier)
```bash
# Type check and SvelteKit verification
docker exec zenengr-frontend-dev-1 npm run check

# Lint and format
docker exec zenengr-frontend-dev-1 npm run lint
```

---

## 🚢 Production Deployment & CI/CD

ZenEngr includes an automated GitHub Actions deployment pipeline ([`.github/workflows/deploy.yml`](.github/workflows/deploy.yml)).

### CI/CD Workflow:
1. **Frontend Deployment**:
   - Compiles SvelteKit into a static Single Page Application (SPA) with Apache `.htaccess` fallback routing.
   - Deploys static build files directly to your frontend subdomain web directory via FTPS.
2. **Backend Deployment**:
   - Syncs `backend/` and `passenger_wsgi.py` via SSH.
   - Injects production secrets from `BACKEND_PROD_ENV`.
   - Activates Python virtual environment and installs dependencies.
   - Automatically runs `alembic upgrade head` to apply database schema migrations to Neon.
   - Touches `tmp/restart.txt` to trigger zero-downtime application reloads.

For detailed setup steps and secret configuration, see [**`docs/deployment-and-cicd.md`**](docs/deployment-and-cicd.md).

---

## 📚 Project Documentation

All specifications, architectural blueprints, and standards live in the [`docs/`](docs/) directory:

* [`docs/deployment-and-cicd.md`](docs/deployment-and-cicd.md) — Production hosting & CI/CD pipeline reference.
* [`docs/frontend-standard.md`](docs/frontend-standard.md) — Svelte 5 & UI conventions.
* [`docs/backend-standard.md`](docs/backend-standard.md) — FastAPI, multi-tenancy, and API standards.
* [`docs/ui-ux-spec.md`](docs/ui-ux-spec.md) — Design tokens, aesthetics, and layout guidelines.
* [`docs/progress.md`](docs/progress.md) — Feature tracker and delivery log.

---

## 📄 License
Private & Proprietary. All rights reserved.
