import uuid
from datetime import datetime, timedelta, timezone

import msal
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.repositories import microsoft as token_repo

SCOPES = ["Files.Read", "User.Read", "offline_access"]

def _get_msal_client() -> msal.ConfidentialClientApplication:
    settings = get_settings()
    authority = f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}"
    return msal.ConfidentialClientApplication(
        settings.microsoft_client_id,
        authority=authority,
        client_credential=settings.microsoft_client_secret,
    )

def get_auth_url(redirect_uri: str, state: str) -> str:
    """Generate the Microsoft OAuth2 authorization URL."""
    client = _get_msal_client()
    return client.get_authorization_request_url(
        SCOPES,
        redirect_uri=redirect_uri,
        state=state,
        response_type="code"
    )

async def exchange_code(
    db: AsyncSession,
    user_id: uuid.UUID,
    code: str,
    redirect_uri: str
) -> dict:
    """Exchange authorization code for tokens and save them."""
    client = _get_msal_client()
    result = client.acquire_token_by_authorization_code(
        code, SCOPES, redirect_uri=redirect_uri
    )
    
    if "error" in result:
        raise ValueError(f"MSAL Error: {result.get('error_description')}")
        
    access_token = result["access_token"]
    refresh_token = result.get("refresh_token")
    expires_in = result.get("expires_in", 3600)
    
    # MSAL handles UTC natively
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    
    await token_repo.save_tokens(
        db, user_id, access_token, refresh_token, expires_at
    )
    
    return result

async def get_valid_access_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Return a valid access token, automatically refreshing if necessary."""
    tokens = await token_repo.get_tokens(db, user_id)
    if not tokens:
        raise ValueError("No Microsoft credentials found for user")
        
    # Check if token is expired or close to expiring (within 5 mins)
    now = datetime.now(timezone.utc)
    # Be aware: some DBs store timezone-naive datetime in UTC, so we might need to cast to aware
    expires_at = tokens["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
        
    if now + timedelta(minutes=5) < expires_at:
        return tokens["access_token"]
        
    # Token expired, acquire new using refresh token
    client = _get_msal_client()
    result = client.acquire_token_by_refresh_token(
        tokens["refresh_token"], SCOPES
    )
    
    if "error" in result:
        raise ValueError(f"Failed to refresh Microsoft token: {result.get('error_description')}")
        
    new_access_token = result["access_token"]
    new_refresh_token = result.get("refresh_token", tokens["refresh_token"])
    new_expires_in = result.get("expires_in", 3600)
    new_expires_at = now + timedelta(seconds=new_expires_in)
    
    await token_repo.save_tokens(
        db, user_id, new_access_token, new_refresh_token, new_expires_at
    )
    
    return new_access_token
