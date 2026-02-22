import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.models.base import Base


class Document(Base):
    """Individual document discovered in a registered OneDrive folder.

    status lifecycle:
        discovered → queued → downloading → downloaded
                   → extracting → extracted → routing
                   → auto_approved | pending_review | rejected
        Any step can transition to: downloading_failed | extraction_failed
    format values: pdf | tiff | jpeg | png
    """

    __tablename__ = "documents"
    __table_args__ = (
        # Primary access pattern: all docs in an engagement with a given status.
        Index("idx_documents_engagement_status", "engagement_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    format: Mapped[str] = mapped_column(String(10), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    onedrive_item_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="discovered"
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    error_detail: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    discovered_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    downloaded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
