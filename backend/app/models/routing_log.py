import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base


class RoutingLog(Base):
    """Record of every routing decision made by the confidence engine.

    decision values: auto_approved | pending_review
    confidence: extraction confidence at routing time (0.0000–1.0000)
    threshold: engagement threshold / 100 at routing time (0.0000–1.0000)
    """

    __tablename__ = "routing_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id")
    )
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("engagements.id")
    )
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    routed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
