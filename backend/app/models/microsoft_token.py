import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base

class MicrosoftToken(Base):
    """Encrypted Microsoft Graph OAuth tokens.
    
    Tied 1:1 with the User who initiated the OAuth flow.
    """

    __tablename__ = "microsoft_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    # Graph API dictates short-lived access tokens (~1 hr) and long-lived refresh tokens (~90 days).
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    # We encrypt the refresh token securely at rest with Fernet
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
