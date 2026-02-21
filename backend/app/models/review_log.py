import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base


class ReviewLog(Base):
    """Immutable audit log of reviewer actions.

    This table is INSERT-ONLY. A PostgreSQL trigger
    (enforce_review_log_immutability) raises an exception on any
    UPDATE or DELETE attempt, both at the DB level and as a safety net
    for application-layer bugs.

    action values: confirm | correct | reject
    corrected_values: only populated when action == 'correct'
    """

    __tablename__ = "review_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id")
    )
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id")
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    corrected_values: Mapped[dict | None] = mapped_column(JSONB)
    # Snapshot of extraction confidence at review time
    confidence_at_review: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    reviewed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
