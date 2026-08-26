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

## 2. GitHub Secrets & Variables Configuration

Go to **GitHub Repository $\rightarrow$ Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**.

### A. Repository Variables (Non-sensitive Config)
Click **New repository variable**:

| Variable Name | Description | Example Value |
| :--- | :--- | :--- |
| `FRONTEND_PUBLIC_API_URL` | Public URL of your FastAPI backend | `https://api.yourdomain.com/api/v1` |

### B. Repository Secrets (Encrypted Credentials)
Click **New repository secret**:

#### 1. Deployment Credentials (Connecting to cPanel)
| Secret Name | Description | Example Value |
| :--- | :--- | :--- |
| `CPANEL_SSH_HOST` | cPanel Server IP or Hostname | `server123.yourhost.com` |
| `CPANEL_SSH_USER` | cPanel Username | `mycpaneluser` |
| `CPANEL_SSH_KEY` | Private SSH Key (OpenSSH format) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `CPANEL_FTP_SERVER` | FTP Hostname for frontend upload | `ftp.yourdomain.com` |
| `CPANEL_FTP_USERNAME` | FTP Username | `deploy@yourdomain.com` |
| `CPANEL_FTP_PASSWORD` | FTP Password | `strong_ftp_password` |
| `CPANEL_FRONTEND_DIR` | *(Optional)* cPanel frontend directory | `/public_html/app/` (Default: `/public_html/`) |
| `CPANEL_BACKEND_DIR` | *(Optional)* cPanel backend directory | `~/api.yourdomain.com` |

#### 2. Production Environment Variables (50–100+ Envs in Single Secrets)
| Secret Name | Description |
| :--- | :--- |
| `BACKEND_PROD_ENV` | Paste your **entire multiline production `backend/.env`** here |
| `FRONTEND_PROD_ENV` | *(Optional)* Paste your **production `frontend/.env`** here |

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

### Frontend Subdomain Setup:
1. In cPanel, go to **Domains $\rightarrow$ Create A New Domain**.
2. Domain: `app.yourdomain.com`.
3. Document Root: `/home/user/public_html/app` (or `/home/user/app.yourdomain.com`).

### Backend Subdomain Setup (Python App):
1. In cPanel, open **Setup Python App**.
2. Click **Create Application**:
   - **Python version**: `3.11` or `3.12` / `3.14`.
   - **Application root**: `api.yourdomain.com`.
   - **Application URL**: `api.yourdomain.com`.
   - **Application startup file**: `passenger_wsgi.py`.
   - **Application Entry point**: `application`.
3. Create `passenger_wsgi.py` in `api.yourdomain.com`:
   ```python
   import sys, os
   sys.path.insert(0, os.path.dirname(__file__) + "/backend")
   from app.main import create_app
   application = create_app()
   ```
