"""Router registration.

Import every feature router here and add it to ``register_routers``.
This keeps ``main.py`` free of per-feature imports.
"""

from fastapi import FastAPI

from app.routers.health import router as health_router


def register_routers(app: FastAPI) -> None:
    # Ops / infra — no /api prefix so the health probe works at the root
    app.include_router(health_router)
