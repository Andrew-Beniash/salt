from fastapi import FastAPI

app = FastAPI(
    title="Salt API",
    description="Tax Automation Platform — backend API",
    version="0.1.0",
)


@app.get("/health", tags=["ops"])
async def health() -> dict:
    """Liveness probe used by Docker health checks and load balancers."""
    return {"status": "ok"}
