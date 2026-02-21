"""Ingestion Celery tasks.

Task chain for a single engagement activation:

  ingest_engagement(engagement_id)
      └─ discovers documents in every registered OneDrive folder
      └─ creates document rows (status=queued)
      └─ (future) chains into extraction tasks per document
"""

from __future__ import annotations

import logging

from app.celery_app import app

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    name="app.tasks.ingestion.ingest_engagement",
    max_retries=3,
    default_retry_delay=60,
)
def ingest_engagement(self, engagement_id: str) -> dict:
    """Discover and queue documents for an engagement.

    This task runs on the ``ingestion`` queue.  It is the entry point
    dispatched by POST /engagements/{id}/activate.

    Current state: stub implementation — logs receipt and returns.
    Full implementation (OneDrive scanning, document row creation, and
    extraction task chaining) is delivered in P3-T02.
    """
    logger.info(
        "ingest_engagement started | engagement_id=%s | attempt=%d",
        engagement_id,
        self.request.retries + 1,
    )

    # ── TODO (P3-T02): replace stub with real ingestion ───────────────────
    # 1. Load engagement + onedrive_folders from DB (sync session)
    # 2. For each folder, list files via Microsoft Graph API
    # 3. For each new file, INSERT into documents (status=queued)
    # 4. Chain extraction tasks:  extract_document.si(doc_id) per document
    # ─────────────────────────────────────────────────────────────────────

    logger.info(
        "ingest_engagement completed (stub) | engagement_id=%s",
        engagement_id,
    )
    return {"status": "queued", "engagement_id": engagement_id}
