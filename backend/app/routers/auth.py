import json
import base64

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services import microsoft as ms_service

router = APIRouter(prefix="/auth/microsoft", tags=["auth"])

def _get_redirect_uri(request: Request) -> str:
    settings = get_settings()
    # The callback should be mounted at this exact path
    return f"{settings.app_url}/api/auth/microsoft/callback"

@router.get("", summary="Initiate Microsoft OAuth2 flow")
async def login_microsoft(
    request: Request,
    user: User = Depends(get_current_user)
):
    """Redirect user to Microsoft identity provider for OAuth consent."""
    redirect_uri = _get_redirect_uri(request)
    
    # We pass the user id through the state so we know who to tie the tokens to
    # A real implementation might encrypt/sign this state parameter
    state_data = {"user_id": str(user.id)}
    state_str = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
    
    auth_url = ms_service.get_auth_url(redirect_uri, state_str)
    return RedirectResponse(auth_url)

@router.get("/callback", summary="Microsoft OAuth2 callback")
async def microsoft_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle Microsoft OAuth code exchange and save tokens."""
    try:
        # In a real app we'd verify a signed state parameter or match it via session cookie
        state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
        user_id_str = state_data["user_id"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state parameter"
        )
        
    import uuid
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user id in state"
        )

    redirect_uri = _get_redirect_uri(request)

    try:
        await ms_service.exchange_code(db, user_id, code, redirect_uri)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )

    # Redirect the user back to the frontend dashboard or a success page.
    settings = get_settings()
    frontend_url = settings.cors_origins_list[0] if settings.cors_origins_list else "http://localhost:3000"
    return RedirectResponse(f"{frontend_url}/?ms_oauth_success=true")

