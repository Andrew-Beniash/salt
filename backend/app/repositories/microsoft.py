from __future__ import annotations

import uuid
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import get_settings
from app.models.microsoft_token import MicrosoftToken

def _get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.fernet_key.encode())

async def save_tokens(
    db: AsyncSession,
    user_id: uuid.UUID,
    access_token: str,
    refresh_token: str,
    expires_at: datetime
) -> MicrosoftToken:
    f = _get_fernet()
    enc_access = f.encrypt(access_token.encode()).decode()
    enc_refresh = f.encrypt(refresh_token.encode()).decode()

    result = await db.execute(select(MicrosoftToken).where(MicrosoftToken.user_id == user_id))
    token_record = result.scalar_one_or_none()

    if token_record:
        token_record.access_token = enc_access
        token_record.refresh_token = enc_refresh
        token_record.expires_at = expires_at
    else:
        token_record = MicrosoftToken(
            user_id=user_id,
            access_token=enc_access,
            refresh_token=enc_refresh,
            expires_at=expires_at
        )
        db.add(token_record)
    
    await db.commit()
    await db.refresh(token_record)
    return token_record

async def get_tokens(db: AsyncSession, user_id: uuid.UUID) -> dict | None:
    result = await db.execute(select(MicrosoftToken).where(MicrosoftToken.user_id == user_id))
    token_record = result.scalar_one_or_none()
    
    if not token_record:
        return None
        
    f = _get_fernet()
    try:
        access_token = f.decrypt(token_record.access_token.encode()).decode()
        refresh_token = f.decrypt(token_record.refresh_token.encode()).decode()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": token_record.expires_at
        }
    except Exception:
        # If decryption fails for some reason (e.g. key rotation without migration)
        # consider the tokens invalid
        return None
