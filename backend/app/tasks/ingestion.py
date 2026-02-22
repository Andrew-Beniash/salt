"""Ingestion Celery tasks.

Task chain for a single engagement activation:

  ingest_engagement(engagement_id)
      └─ resolves creator's Microsoft access token (auto-refreshes if expired)
      └─ discovers ALL files in every registered OneDrive folder (recursive)
      └─ handles @odata.nextLink pagination (>200 items per folder)
      └─ creates document rows (status=discovered), skipping already-known items
      └─ chains into → validate_documents(engagement_id)

  validate_documents(engagement_id)
      └─ enforces 50,000-document engagement cap (oldest-first; excess → rejected)
      └─ validates MIME type derived from filename (PDF/TIFF/JPEG/PNG accepted)
      └─ validates file size > 0 bytes
      └─ moves passing documents → validated; failures → rejected + rejection_reason
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import os
import uuid

import httpx
from sqlalchemy import func
from sqlalchemy.future import select

from app.celery_app import app
from app.config import get_settings
from app.database import get_session_factory
from app.models.document import Document
from app.models.engagement import Engagement, OneDriveFolder
from app.services import microsoft as ms_service

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Canonical format values for supported extensions (tif→tiff, jpg→jpeg).
_EXT_TO_FORMAT: dict[str, str] = {
    "pdf": "pdf",
    "tiff": "tiff",
    "tif": "tiff",
    "jpeg": "jpeg",
    "jpg": "jpeg",
    "png": "png",
}

# MIME types accepted for extraction.
_SUPPORTED_MIME_TYPES: frozenset[str] = frozenset({
    "application/pdf",
    "image/tiff",
    "image/jpeg",
    "image/png",
})

# Per-engagement document cap (FR-011).
_MAX_DOCUMENTS: int = 50_000


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
    """Recursively list ALL files under *folder_path* on the user's OneDrive.

    Every file — regardless of extension — is returned.  Format filtering and
    MIME-type validation are deferred to ``validate_documents`` so that
    unsupported files are explicitly rejected with a stored reason rather than
    silently skipped.  Sub-folders are traversed depth-first.
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
            files.append(item)  # include all file types

    return files


# ── ingest_engagement ──────────────────────────────────────────────────────────


async def _ingest(engagement_id: str) -> dict:
    """Discover files via Graph API and persist a Document row per new file."""
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

        # 4. Discover ALL files; insert new Document rows ──────────────────────
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
                    "Found %d files | engagement_id=%s | folder=%s",
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
                    # Use canonical format for known types; store raw extension
                    # (capped at 10 chars) for unknown types so the column stays
                    # non-null while validate_documents can still reject the row.
                    fmt = _EXT_TO_FORMAT.get(ext, ext[:10] if ext else "unknown")

                    doc = Document(
                        engagement_id=eng_uuid,
                        filename=item["name"],
                        format=fmt,
                        source_url=(
                            item.get("@microsoft.graph.downloadUrl")
                            or item.get("webUrl")
                        ),
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


@app.task(
    bind=True,
    name="app.tasks.ingestion.ingest_engagement",
    max_retries=3,
    default_retry_delay=60,
)
def ingest_engagement(self, engagement_id: str) -> dict:
    """Discover documents for an engagement and chain into format validation.

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
        result = asyncio.run(_ingest(engagement_id))
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

    # Chain into format / size validation.
    validate_documents.apply_async(args=[engagement_id], queue="ingestion")
    return result


# ── validate_documents ─────────────────────────────────────────────────────────


async def _validate(engagement_id: str) -> dict:
    """Apply format, size, and cap rules to all *discovered* documents."""
    eng_uuid = uuid.UUID(engagement_id)
    factory = get_session_factory()

    async with factory() as db:
        # Count documents already past the discovery/validation stage so that
        # re-runs of ingest + validate honour the cap correctly.
        cap_result = await db.execute(
            select(func.count(Document.id)).where(
                Document.engagement_id == eng_uuid,
                Document.status.notin_(["discovered", "rejected"]),
            )
        )
        already_counted: int = cap_result.scalar() or 0

        # Load all documents still in the *discovered* state, oldest first, so
        # the cap is applied on a first-come-first-served basis.
        doc_result = await db.execute(
            select(Document)
            .where(
                Document.engagement_id == eng_uuid,
                Document.status == "discovered",
            )
            .order_by(Document.discovered_at)
        )
        documents = list(doc_result.scalars().all())

        validated = 0
        rejected = 0

        for doc in documents:
            # ── 1. Engagement cap (FR-011) ────────────────────────────────────
            if already_counted + validated >= _MAX_DOCUMENTS:
                doc.status = "rejected"
                doc.rejection_reason = "Engagement document limit exceeded"
                rejected += 1
                continue

            # ── 2. MIME type validation (FR-008) ──────────────────────────────
            mime_type, _ = mimetypes.guess_type(doc.filename)
            if mime_type not in _SUPPORTED_MIME_TYPES:
                doc.status = "rejected"
                doc.rejection_reason = (
                    f"Unsupported file format: {mime_type}"
                    if mime_type
                    else "File format could not be determined from filename"
                )
                rejected += 1
                continue

            # ── 3. File size validation (FR-009) ──────────────────────────────
            if not doc.file_size_bytes or doc.file_size_bytes <= 0:
                doc.status = "rejected"
                doc.rejection_reason = "File is empty (zero bytes)"
                rejected += 1
                continue

            doc.status = "validated"
            validated += 1

        await db.commit()

    logger.info(
        "validate_documents done | engagement_id=%s | validated=%d | rejected=%d",
        engagement_id,
        validated,
        rejected,
    )
    return {
        "status": "complete",
        "engagement_id": engagement_id,
        "validated": validated,
        "rejected": rejected,
    }


@app.task(
    bind=True,
    name="app.tasks.ingestion.validate_documents",
    max_retries=3,
    default_retry_delay=60,
)
def validate_documents(self, engagement_id: str) -> dict:
    """Validate format and size for all discovered documents in an engagement.

    This task runs on the ``ingestion`` queue.  It is chained automatically
    after ``ingest_engagement`` completes.

    Validation rules applied in order:

    1. **Engagement cap** (FR-011): documents beyond ``_MAX_DOCUMENTS`` per
       engagement are rejected with reason "Engagement document limit exceeded".
       Evaluation is oldest-first (``discovered_at`` ASC) so earlier files are
       always prioritised.

    2. **MIME type** (FR-008): only ``application/pdf``, ``image/tiff``,
       ``image/jpeg``, and ``image/png`` are accepted.  The MIME type is
       derived from the filename using ``mimetypes.guess_type``.  Any other
       type (e.g. ``application/vnd.openxmlformats-officedocument…`` for Word/
       Excel) is rejected with a descriptive reason.

    3. **File size** (FR-009): zero-byte or null-size files are rejected with
       reason "File is empty (zero bytes)".

    Documents that pass all three checks are moved to ``validated``.  Failures
    are moved to ``rejected`` with a human-readable ``rejection_reason``.
    """
    logger.info(
        "validate_documents started | engagement_id=%s | attempt=%d",
        engagement_id,
        self.request.retries + 1,
    )

    try:
        return asyncio.run(_validate(engagement_id))
    except ValueError as exc:
        logger.error(
            "validate_documents failed (non-retryable) | engagement_id=%s | error=%s",
            engagement_id,
            exc,
        )
        raise
    except Exception as exc:
        logger.warning(
            "validate_documents error | engagement_id=%s | attempt=%d | error=%s",
            engagement_id,
            self.request.retries + 1,
            exc,
        )
        raise self.retry(exc=exc)

    # Chain into populate_queue
    populate_queue.apply_async(args=[engagement_id], queue="ingestion")
    return result

# ── download_document ──────────────────────────────────────────────────────────

async def _download(document_id: str) -> dict:
    """Stream download document from graph api URL."""
    doc_uuid = uuid.UUID(document_id)
    factory = get_session_factory()
    settings = get_settings()

    async with factory() as db:
        result = await db.execute(select(Document).where(Document.id == doc_uuid))
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        if not doc.source_url:
            doc.status = "download_failed"
            doc.error_detail = "No source URL available for download"
            await db.commit()
            raise ValueError(doc.error_detail)

        eng_dir = os.path.join(settings.storage_path, str(doc.engagement_id))
        os.makedirs(eng_dir, exist_ok=True)

        ext = doc.format if doc.format else "bin"
        filename = f"{document_id}.{ext}"
        filepath = os.path.join(eng_dir, filename)

        doc.status = "downloading"
        await db.commit()
        await db.refresh(doc)

        try:
            # Setting timeout=None for streaming large files without dropping connects
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", doc.source_url) as response:
                    response.raise_for_status()
                    with open(filepath, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
            
            doc.storage_path = filepath
            doc.status = "downloaded"
            doc.downloaded_at = func.now()
            await db.commit()
            
        except Exception:
            raise

    # Trigger extraction task immediately for this downloaded document
    # Status remains 'downloaded' as per the lifecycle docstring, until extracting begins
    from app.tasks.extraction import extract_document
    extract_document.apply_async(args=[document_id], queue="extraction")

    logger.info(
        "download_document done | document_id=%s | path=%s",
        document_id,
        filepath
    )
    return {
        "status": "downloaded",
        "document_id": document_id,
        "storage_path": filepath
    }

async def _mark_download_failed(document_id: str, error_detail: str) -> None:
    doc_uuid = uuid.UUID(document_id)
    factory = get_session_factory()
    async with factory() as db:
        result = await db.execute(select(Document).where(Document.id == doc_uuid))
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = "download_failed"
            doc.error_detail = error_detail
            await db.commit()

@app.task(
    bind=True,
    name="app.tasks.ingestion.download_document",
    max_retries=3,
)
def download_document(self, document_id: str) -> dict:
    """Download the document content from OneDrive to local storage.
    
    Writes to /storage/{engagement_id}/{document_id}.{ext}.
    Handles streaming for large files over 50MB.
    Updates the document record with the download status and path.
    """
    logger.info(
        "download_document started | document_id=%s | attempt=%d",
        document_id,
        self.request.retries + 1,
    )

    try:
        return asyncio.run(_download(document_id))
    except ValueError as exc:
        logger.error(
            "download_document failed (non-retryable) | document_id=%s | error=%s",
            document_id,
            exc,
        )
        raise
    except Exception as exc:
        delays = [10, 30, 90]
        retries = self.request.retries
        
        if retries >= len(delays):
            logger.error(
                "download_document final failure | document_id=%s | error=%s",
                document_id,
                exc,
            )
            asyncio.run(_mark_download_failed(document_id, f"Final failure after retries: {exc}"))
            raise
            
        logger.warning(
            "download_document error | document_id=%s | attempt=%d | error=%s. Retrying in %ds",
            document_id,
            retries + 1,
            exc,
            delays[retries],
        )
        raise self.retry(exc=exc, countdown=delays[retries])

# ── populate_queue ─────────────────────────────────────────────────────────────

async def _populate(engagement_id: str) -> dict:
    eng_uuid = uuid.UUID(engagement_id)
    factory = get_session_factory()
    
    async with factory() as db:
        result = await db.execute(
            select(Document)
            .where(
                Document.engagement_id == eng_uuid,
                Document.status == "validated"
            )
            .order_by(Document.discovered_at)
            .limit(100)
        )
        docs = list(result.scalars().all())
        
        if not docs:
            return {"status": "complete", "queued_count": 0}
            
        for doc in docs:
            doc.status = "queued"
            
        await db.commit()
    
    # Dispatch after commit to avoid workers picking up tasks before state changes
    for doc in docs:
        download_document.apply_async(args=[str(doc.id)], queue="ingestion")
        
    logger.info(
        "populate_queue dispatched | engagement_id=%s | count=%d",
        engagement_id,
        len(docs)
    )
    return {"status": "continuing", "queued_count": len(docs)}

@app.task(
    bind=True, 
    name="app.tasks.ingestion.populate_queue", 
    max_retries=3,
    default_retry_delay=30
)
def populate_queue(self, engagement_id: str) -> dict:
    """Batch dispatch validated documents to the download queue to avoid overwhelming Redis.
    
    Processes up to 100 documents per execution, updating their status to 'queued',
    and dispatches them. If there are more documents remaining, recursive chaining continues.
    """
    logger.info(
        "populate_queue started | engagement_id=%s | attempt=%d",
        engagement_id,
        self.request.retries + 1,
    )
    
    try:
        result = asyncio.run(_populate(engagement_id))
        
        if result["status"] == "continuing":
            # Schedule another batch immediately to chew through the backlog
            self.apply_async(args=[engagement_id], countdown=2, queue="ingestion")
            
        return result
    except Exception as exc:
        logger.warning(
            "populate_queue error | engagement_id=%s | attempt=%d | error=%s",
            engagement_id,
            self.request.retries + 1,
            exc,
        )
        raise self.retry(exc=exc)

