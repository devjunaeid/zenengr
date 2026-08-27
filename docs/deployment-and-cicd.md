# Monorepo Deployment & CI/CD Guide (cPanel + Neon)

This guide documents the automated CI/CD pipeline for deploying the **Frontend** (SvelteKit) and **Backend** (FastAPI) from a single Git repository to **cPanel hosting** connected to **Neon PostgreSQL**.

---

## 1. Architecture Overview

```
                      [ Git Repository (main branch) ]
                                      │
                   ┌──────────────────┴──────────────────┐
                   ▼                                     ▼
        [ frontend/ changes ]                 [ backend/ changes ]
                   │                                     │
                   ▼                                     ▼
         GitHub Action: Frontend               GitHub Action: Backend
         1. npm ci & npm run build             1. SSH to cPanel server
         2. FTPS upload to cPanel web          2. Inject BACKEND_PROD_ENV (.env)
            directory (e.g. app.domain.com)    3. uv sync & alembic upgrade head
                                               4. touch tmp/restart.txt (Passenger)
```

---

## 2. GitHub Secrets Configuration

Go to **GitHub Repository $\rightarrow$ Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions $\rightarrow$ Secrets tab**.

Click **New repository secret**:

### 1. Deployment Credentials (Connecting to cPanel)
| Secret Name | Description | Value |
| :--- | :--- | :--- |
| `CPANEL_SSH_HOST` | cPanel Server IP or Hostname | `synafeia.com` (or your cPanel Server IP) |
| `CPANEL_SSH_USER` | cPanel Username | `enginee2` |
| `CPANEL_SSH_KEY` | Private SSH Key (OpenSSH format) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `CPANEL_FTP_SERVER` | FTP Hostname for frontend upload | `synafeia.com` (or FTP host) |
| `CPANEL_FTP_USERNAME` | FTP Username | `deploy@zenengr.synafeia.com` (or cPanel FTP user) |
| `CPANEL_FTP_PASSWORD` | FTP Password | `your_ftp_password` |
| `CPANEL_FRONTEND_DIR` | cPanel frontend directory | `/zenengr.synafeia.com/` (or `/home/enginee2/zenengr.synafeia.com/`) |
| `CPANEL_BACKEND_DIR` | cPanel backend directory | `/home/enginee2/api-zenengr.synafeia.com` |
| `CPANEL_VENV_BIN` | *(Optional)* Virtualenv bin path | `/home/enginee2/virtualenv/api-zenengr.synafeia.com/3.12/bin` |

### 2. Application Environment Secrets (Single Multiline Secrets)
| Secret Name | Description |
| :--- | :--- |
| `FRONTEND_PROD_ENV` | Paste your **entire `frontend/.env.production`** content here |
| `BACKEND_PROD_ENV` | Paste your **entire `backend/.env.production`** content here |

**Example content for `BACKEND_PROD_ENV`**:
```env
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://neondb_owner:***@ep-***.neon.tech/neondb?ssl=require
CACHE_BACKEND=memory
JWT_SECRET=super-secure-production-random-jwt-key
CORS_ORIGINS=https://app.yourdomain.com
ADMIN_PORTAL_BASE_URL=https://app.yourdomain.com
CLIENT_PORTAL_BASE_URL=https://app.yourdomain.com/client
INVITE_TTL_HOURS=72
PASSWORD_RESET_TTL_HOURS=24
STORAGE_BACKEND=local
STORAGE_LOCAL_DIR=storage
UPLOADS_DIR=uploads
```

**Example content for `FRONTEND_PROD_ENV`**:
```env
PUBLIC_API_URL=https://api.yourdomain.com/api/v1
PUBLIC_APP_NAME="ZenEngr"
```

> **Why this single secret approach scales**:
> When you have 50–100+ environment variables, you never need to edit YAML files or add 100 individual items in GitHub UI. Just edit `BACKEND_PROD_ENV` in GitHub Settings and the next deployment updates the server automatically!

---

## 3. Local vs Production Environment Organization

```
zenengr/
├── .env                      <-- Local Docker Compose development
├── .env.example              <-- Template for root dev stack
│
├── frontend/
│   ├── .env                  <-- Local frontend development (PUBLIC_API_URL=http://localhost:8000/api/v1)
│   └── .env.example          <-- Template for frontend
│
└── backend/
    ├── .env                  <-- Local backend development
    └── .env.example          <-- Template for backend
```

---

## 4. Initial cPanel Setup
1. Domain: `zenengr.synafeia.com` (Document Root: `/home/enginee2/zenengr.synafeia.com`)
2. In cPanel, open **Setup Python App**:
   - **Python version**: `3.11` or `3.12`
   - **Application root**: `api-zenengr.synafeia.com` (maps to `/home/enginee2/api-zenengr.synafeia.com`)
   - **Application URL**: `api-zenengr.synafeia.com`
   - **Application startup file**: `passenger_wsgi.py`
   - **Application Entry point**: `application`
3. In `/home/enginee2/api-zenengr.synafeia.com`, create `passenger_wsgi.py`:
   ```python
   import sys, os
   sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
   from app.main import create_app
   application = create_app()
   ```
4. Clone the repository once into `/home/enginee2/api-zenengr.synafeia.com`:
   ```bash
   cd /home/enginee2/api-zenengr.synafeia.com
   git clone <your-repo-url> .
   ```
