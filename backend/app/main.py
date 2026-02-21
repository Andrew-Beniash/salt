from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate all required settings before the server accepts traffic.

    Pydantic raises a descriptive ValidationError here (not buried in a 500)
    if any required environment variable is absent or invalid.
    """
    get_settings()  # raises ValidationError with field-level detail if misconfigured
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or get_settings()

    application = FastAPI(
        title="Salt API",
        description="Tax Automation Platform — backend API",
        version="0.1.0",
        docs_url="/docs" if cfg.app_env != "production" else None,
        redoc_url="/redoc" if cfg.app_env != "production" else None,
        lifespan=lifespan,
    )

    return application


app = create_app()


@app.get("/health", tags=["ops"])
async def health() -> dict:
    """Liveness probe used by Docker health checks and load balancers."""
    return {"status": "ok"}
