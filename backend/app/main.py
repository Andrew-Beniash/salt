"""FastAPI application factory.

Call ``create_app()`` to build a fully-configured FastAPI instance.
The module-level ``app`` object is what uvicorn / the Dockerfile CMD uses.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.config import Settings, get_settings
from app.routers import register_routers


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate all required settings before the server accepts traffic.

    Pydantic raises a descriptive ``ValidationError`` here — not buried inside
    a 500 response — if any required environment variable is absent or invalid.
    """
    get_settings()
    yield


# ── Exception handlers ────────────────────────────────────────────────────────

def _register_exception_handlers(app: FastAPI, cfg: Settings) -> None:
    """Register global exception handlers that produce consistent JSON errors."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "status_code": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "status_code": 422},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        # Never leak internal tracebacks in production.
        detail = (
            "An unexpected error occurred."
            if cfg.app_env == "production"
            else repr(exc)
        )
        return JSONResponse(
            status_code=500,
            content={"detail": detail, "status_code": 500},
        )


# ── App factory ───────────────────────────────────────────────────────────────

def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application.

    Args:
        settings: Pre-constructed Settings instance (mainly for tests).
                  Falls back to ``get_settings()`` when omitted.
    """
    cfg = settings or get_settings()

    application = FastAPI(
        title="Salt API",
        description="Tax Automation Platform — backend API",
        version=__version__,
        # Docs only available outside production; accessible at /api/docs
        docs_url="/api/docs" if cfg.app_env != "production" else None,
        redoc_url="/api/redoc" if cfg.app_env != "production" else None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    # Reads the comma-separated CORS_ORIGINS setting.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Trusted hosts ─────────────────────────────────────────────────────────
    # In development, allow all hosts ("*").
    # In staging/production, restrict to the APP_URL hostname so that
    # Host-header injection attacks are rejected at the middleware layer.
    if cfg.app_env == "development":
        allowed_hosts: list[str] = ["*"]
    else:
        host = urlparse(cfg.app_url).hostname or "localhost"
        allowed_hosts = [host, f"*.{host}"]

    application.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    # ── Global exception handlers ─────────────────────────────────────────────
    _register_exception_handlers(application, cfg)

    # ── Routers ───────────────────────────────────────────────────────────────
    register_routers(application)

    return application


app = create_app()
