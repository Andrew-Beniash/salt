import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base


class Extraction(Base):
    """AI extraction result for a single document.

    One document has at most one extraction record (unique index on document_id).
    confidence: NUMERIC(5,4) → 0.0000–1.0000.
    extraction_method values: pdfplumber | azure_di | openai
    fields: {"sales_tax": "1245.00", "date": "2024-03-15", ...}
    """

    __tablename__ = "extractions"
    __table_args__ = (
        # Enforces the one-extraction-per-document invariant at the DB level.
        Index("idx_extractions_document", "document_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
    )
    # {"sales_tax": "1245.00", "date": "2024-03-15", "jurisdiction": "CA"}
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    extraction_method: Mapped[str] = mapped_column(String(50), nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    extracted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
