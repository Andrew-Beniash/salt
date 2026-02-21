from fastapi import APIRouter, Request

router = APIRouter(tags=["ops"])


@router.get(
    "/health",
    summary="Liveness probe",
    response_description="Service is up and running",
)
async def health(request: Request) -> dict:
    """Return service status and current API version.

    Used by Docker health checks, load balancers, and monitoring systems.
    Always returns HTTP 200 while the process is alive.
    """
    return {"status": "ok", "version": request.app.version}
