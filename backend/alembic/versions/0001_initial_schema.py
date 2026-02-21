"""Initial schema — all core tables, indexes, and review_log trigger.

Revision ID: 0001
Revises:
Create Date: 2026-02-21
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Trigger SQL (§4.7 — Audit Log Immutability) ───────────────────────────────

_CREATE_IMMUTABILITY_FUNCTION = """
CREATE OR REPLACE FUNCTION prevent_review_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'review_log is immutable. Modifications are not permitted.';
END;
$$ LANGUAGE plpgsql;
"""

_CREATE_IMMUTABILITY_TRIGGER = """
CREATE TRIGGER enforce_review_log_immutability
    BEFORE UPDATE OR DELETE ON review_log
    FOR EACH ROW EXECUTE FUNCTION prevent_review_log_modification();
"""


# ── upgrade ───────────────────────────────────────────────────────────────────

def upgrade() -> None:
    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # ── engagements ───────────────────────────────────────────────────────────
    op.create_table(
        "engagements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("client_id", sa.String(100), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("project_name", sa.String(255), nullable=False),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default="draft"
        ),
        sa.Column(
            "confidence_threshold",
            sa.Integer(),
            nullable=False,
            server_default="85",
        ),
        sa.Column("output_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── engagement_members ────────────────────────────────────────────────────
    op.create_table(
        "engagement_members",
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role", sa.String(50), nullable=False, server_default="reviewer"
        ),
        sa.Column(
            "added_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── onedrive_folders ──────────────────────────────────────────────────────
    op.create_table(
        "onedrive_folders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("folder_path", sa.Text(), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("microsoft_user", sa.String(255), nullable=True),
        sa.Column(
            "registered_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ── documents ─────────────────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("onedrive_item_id", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="discovered",
        ),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column(
            "discovered_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("processed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_documents_engagement_status",
        "documents",
        ["engagement_id", "status"],
    )

    # ── extractions ───────────────────────────────────────────────────────────
    op.create_table(
        "extractions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("extraction_method", sa.String(50), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "extracted_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    # One extraction per document maximum
    op.create_index(
        "idx_extractions_document",
        "extractions",
        ["document_id"],
        unique=True,
    )

    # ── review_log ────────────────────────────────────────────────────────────
    op.create_table(
        "review_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=True,
        ),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id"),
            nullable=True,
        ),
        sa.Column(
            "reviewer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column(
            "corrected_values",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("confidence_at_review", sa.Numeric(5, 4), nullable=True),
        sa.Column(
            "reviewed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # Immutability: function must exist before the trigger references it
    op.execute(_CREATE_IMMUTABILITY_FUNCTION)
    op.execute(_CREATE_IMMUTABILITY_TRIGGER)

    # ── routing_log ───────────────────────────────────────────────────────────
    op.create_table(
        "routing_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=True,
        ),
        sa.Column(
            "engagement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engagements.id"),
            nullable=True,
        ),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("threshold", sa.Numeric(5, 4), nullable=False),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column(
            "routed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


# ── downgrade ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    op.drop_table("routing_log")

    op.execute(
        "DROP TRIGGER IF EXISTS enforce_review_log_immutability ON review_log"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_review_log_modification()")
    op.drop_table("review_log")

    op.drop_index("idx_extractions_document", table_name="extractions")
    op.drop_table("extractions")

    op.drop_index("idx_documents_engagement_status", table_name="documents")
    op.drop_table("documents")

    op.drop_table("onedrive_folders")
    op.drop_table("engagement_members")
    op.drop_table("engagements")
    op.drop_table("users")
