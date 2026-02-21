"""JWT authentication dependency.

Validates Supabase-issued JWTs (HS256, audience="authenticated") and
provisions the local user row on first login.

Usage::

    from app.dependencies.auth import get_current_user

    @router.get("/protected")
    async def protected(user: User = Depends(get_current_user)):
        ...
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.repositories.users import get_or_create_user

# Points at /api/auth/token so OpenAPI's "Authorize" button works, but the
# actual credential validation is done by Supabase — FastAPI only reads the
# Bearer token that the frontend already obtained.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)

_ALGORITHM = "HS256"
_AUDIENCE = "authenticated"

_401 = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str | None = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Decode and verify the Supabase JWT; return (or create) the local User row.

    Raises HTTP 401 for missing, expired, or tampered tokens.
    """
    if not token:
        raise _401

    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[_ALGORITHM],
            audience=_AUDIENCE,
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise _401

    sub: str | None = payload.get("sub")
    email: str | None = payload.get("email")

    if not sub or not email:
        raise _401

    try:
        user_id = uuid.UUID(sub)
    except ValueError:
        raise _401

    return await get_or_create_user(db, user_id=user_id, email=email)
