"""Ingestion Celery tasks.

Task chain for a single engagement activation:

  ingest_engagement(engagement_id)
      └─ resolves creator's Microsoft access token (auto-refreshes if expired)
      └─ discovers documents in every registered OneDrive folder (recursive)
      └─ handles @odata.nextLink pagination (>200 items per folder)
      └─ creates document rows (status=discovered), skipping already-known items
      └─ (future) chains into extraction tasks per document
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid

import httpx
from sqlalchemy.future import select

from app.celery_app import app
from app.database import get_session_factory
from app.models.document import Document
from app.models.engagement import Engagement, OneDriveFolder
from app.services import microsoft as ms_service

logger = logging.getLogger(__name__)

# Supported file extensions and their canonical format values stored in DB.
_EXT_TO_FORMAT: dict[str, str] = {
    "pdf": "pdf",
    "tiff": "tiff",
    "tif": "tiff",
    "jpeg": "jpeg",
    "jpg": "jpeg",
    "png": "png",
}

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"


# ── Graph API helpers ──────────────────────────────────────────────────────────


async def _list_items(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
) -> list[dict]:
    """Return all items from a Graph children endpoint, following nextLink pages."""
    items: list[dict] = []
    params: dict | None = {
        "$top": 200,
        "$select": "id,name,file,folder,size,webUrl",
    }
    next_url: str | None = url

    while next_url:
        if params:
            response = await client.get(next_url, headers=headers, params=params)
            params = None  # nextLink already embeds query params
        else:
            response = await client.get(next_url, headers=headers)

        response.raise_for_status()
        data = response.json()
        items.extend(data.get("value", []))
        next_url = data.get("@odata.nextLink")

    return items


async def _discover_folder(
    client: httpx.AsyncClient,
    headers: dict,
    folder_path: str,
) -> list[dict]:
    """Recursively list all supported files under *folder_path* on the user's OneDrive.

    Files whose extension is not in ``_EXT_TO_FORMAT`` are silently ignored.
    Sub-folders are traversed depth-first.
    """
    url = f"{_GRAPH_BASE}/me/drive/root:/{folder_path}:/children"
    items = await _list_items(client, url, headers)

    files: list[dict] = []
    for item in items:
        if "folder" in item:
            child_path = f"{folder_path}/{item['name']}"
            child_files = await _discover_folder(client, headers, child_path)
            files.extend(child_files)
        elif "file" in item:
            ext = os.path.splitext(item["name"])[1].lstrip(".").lower()
            if ext in _EXT_TO_FORMAT:
                files.append(item)

    return files


# ── Core async ingestion logic ─────────────────────────────────────────────────


async def _ingest(engagement_id: str) -> dict:
    """Load engagement data, call Graph API, and persist discovered documents."""
    eng_uuid = uuid.UUID(engagement_id)
    factory = get_session_factory()

    async with factory() as db:
        # 1. Load engagement ──────────────────────────────────────────────────
        result = await db.execute(
            select(Engagement).where(Engagement.id == eng_uuid)
        )
        engagement = result.scalar_one_or_none()
        if not engagement:
            raise ValueError(f"Engagement {engagement_id} not found")

        if not engagement.created_by:
            raise ValueError(
                f"Engagement {engagement_id} has no creator; cannot resolve Microsoft token"
            )

        # 2. Resolve a valid access token (silently refreshes when near expiry) ─
        access_token = await ms_service.get_valid_access_token(db, engagement.created_by)
        auth_headers = {"Authorization": f"Bearer {access_token}"}

        # 3. Load registered OneDrive folders ─────────────────────────────────
        folder_result = await db.execute(
            select(OneDriveFolder).where(OneDriveFolder.engagement_id == eng_uuid)
        )
        folders = list(folder_result.scalars().all())

        if not folders:
            raise ValueError(
                f"Engagement {engagement_id} has no registered OneDrive folders"
            )

        # 4. Discover files and insert new document rows ───────────────────────
        discovered = 0
        skipped = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            for folder in folders:
                logger.info(
                    "Scanning folder | engagement_id=%s | folder=%s",
                    engagement_id,
                    folder.folder_path,
                )

                items = await _discover_folder(client, auth_headers, folder.folder_path)
                logger.info(
                    "Found %d supported files | engagement_id=%s | folder=%s",
                    len(items),
                    engagement_id,
                    folder.folder_path,
                )

                for item in items:
                    # Idempotency: skip files already recorded for this engagement.
                    existing = await db.execute(
                        select(Document).where(
                            Document.onedrive_item_id == item["id"],
                            Document.engagement_id == eng_uuid,
                        )
                    )
                    if existing.scalar_one_or_none() is not None:
                        skipped += 1
                        continue

                    ext = os.path.splitext(item["name"])[1].lstrip(".").lower()
                    fmt = _EXT_TO_FORMAT[ext]

                    doc = Document(
                        engagement_id=eng_uuid,
                        filename=item["name"],
                        format=fmt,
                        source_url=item.get("@microsoft.graph.downloadUrl") or item.get("webUrl"),
                        onedrive_item_id=item["id"],
                        file_size_bytes=item.get("size"),
                        status="discovered",
                    )
                    db.add(doc)
                    discovered += 1

        await db.commit()

    logger.info(
        "ingest_engagement done | engagement_id=%s | discovered=%d | skipped=%d",
        engagement_id,
        discovered,
        skipped,
    )
    return {
        "status": "ingested",
        "engagement_id": engagement_id,
        "discovered": discovered,
        "skipped": skipped,
    }


# ── Celery task ────────────────────────────────────────────────────────────────


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

    Retries up to 3 times (60-second delay) on transient Graph API or network
    errors.  Configuration errors (missing engagement, missing Microsoft token)
    raise immediately without retry.
    """
    logger.info(
        "ingest_engagement started | engagement_id=%s | attempt=%d",
        engagement_id,
        self.request.retries + 1,
    )

    try:
        return asyncio.run(_ingest(engagement_id))
    except ValueError as exc:
        # Non-retryable: bad config, engagement not found, no MS token, etc.
        logger.error(
            "ingest_engagement failed (non-retryable) | engagement_id=%s | error=%s",
            engagement_id,
            exc,
        )
        raise
    except Exception as exc:
        logger.warning(
            "ingest_engagement error | engagement_id=%s | attempt=%d | error=%s",
            engagement_id,
            self.request.retries + 1,
            exc,
        )
        raise self.retry(exc=exc)
