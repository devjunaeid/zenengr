from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.client_auth import auth_router as client_auth_router
from app.api.v1.client_auth import public_router as client_auth_public_router
from app.api.v1.client_auth import tenant_router as client_invite_tenant_router
from app.api.v1.health import router as health_router
from app.api.v1.invites import public_router as invite_public_router
from app.api.v1.invites import tenant_router as invite_tenant_router
from app.api.v1.tenant import router as tenant_router
from app.api.v1.users import public_router as users_public_router
from app.api.v1.users import tenant_router as users_tenant_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, tags=["health"])
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(invite_tenant_router)
api_router.include_router(invite_public_router)
api_router.include_router(tenant_router)
api_router.include_router(users_tenant_router)
api_router.include_router(users_public_router)
api_router.include_router(client_auth_router)
api_router.include_router(client_auth_public_router)
api_router.include_router(client_invite_tenant_router)
