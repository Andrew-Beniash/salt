"""Router registration.

Import every feature router here and add it to ``register_routers``.
This keeps ``main.py`` free of per-feature imports.
"""

from fastapi import APIRouter, Depends, FastAPI

from app.routers.health import router as health_router
from app.dependencies.auth import get_current_user
from app.routers.users import router as users_router
from app.routers.tasks import router as tasks_router

def register_routers(app: FastAPI) -> None:
    # Ops / infra — no /api prefix so the health probe works at the root
    app.include_router(health_router)

    # API endpoints — all protected by Supabase JWT validation by default
    api_router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])
    
    # Register feature routers here
    api_router.include_router(users_router)

    app.include_router(api_router)
    app.include_router(tasks_router, prefix="/api")

