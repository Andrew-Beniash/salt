# TaxAutomation Platform — Architectural Specification

**Version 1.0 | February 2026**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architectural Principles](#2-architectural-principles)
3. [System Overview](#3-system-overview)
4. [Component Architecture](#4-component-architecture)
   - 4.1 [API Layer — FastAPI](#41-api-layer--fastapi)
   - 4.2 [Task Queue — Celery + Redis](#42-task-queue--celery--redis)
   - 4.3 [Document Processing Pipeline](#43-document-processing-pipeline)
   - 4.4 [OCR Tier System](#44-ocr-tier-system)
   - 4.5 [AI Extraction Engine](#45-ai-extraction-engine)
   - 4.6 [Confidence & Routing Engine](#46-confidence--routing-engine)
   - 4.7 [Human-in-the-Loop Review](#47-human-in-the-loop-review)
   - 4.8 [Notification Service](#48-notification-service)
   - 4.9 [Export Service](#49-export-service)
   - 4.10 [Frontend Application](#410-frontend-application)
5. [Data Architecture](#5-data-architecture)
   - 5.1 [Database Schema](#51-database-schema)
   - 5.2 [Data Flow](#52-data-flow)
   - 5.3 [Storage Architecture](#53-storage-architecture)
6. [Integration Architecture](#6-integration-architecture)
   - 6.1 [Microsoft Graph API / OneDrive](#61-microsoft-graph-api--onedrive)
   - 6.2 [OpenAI API](#62-openai-api)
   - 6.3 [Azure Document Intelligence](#63-azure-document-intelligence)
   - 6.4 [SendGrid / SMTP](#64-sendgrid--smtp)
   - 6.5 [Supabase Auth](#65-supabase-auth)
7. [Concurrency & Parallelism](#7-concurrency--parallelism)
8. [Security Architecture](#8-security-architecture)
9. [Error Handling & Resilience](#9-error-handling--resilience)
10. [Infrastructure & Deployment](#10-infrastructure--deployment)
11. [Production Migration Path](#11-production-migration-path)
12. [Document Control](#12-document-control)

---

## 1. Introduction

### 1.1 Purpose

This document defines the complete technical architecture of the TaxAutomation Platform initial prototype. It covers system decomposition, component responsibilities, data models, integration patterns, concurrency strategy, security model, and deployment configuration. It is intended as the authoritative technical reference for all engineering decisions on the prototype.

### 1.2 Scope

This specification covers the full prototype system as defined in the product specification (Version 1.0, February 2026). It does not cover enterprise features deferred to subsequent phases, including multi-tenant isolation, advanced RBAC, or production-grade observability infrastructure.

### 1.3 Reference Documents

| Document | Version | Description |
|---|---|---|
| TaxAutomation_Specification.docx | 1.0 | Formal product specification — functional and non-functional requirements |
| TaxAutomation_ProcessOverview.docx | 1.0 | End-to-end process flow and roles |
| TaxAutomation_TechStack.md | 1.0 | Recommended technology stack with rationale |
| TaxAutomation_DevelopmentPlan.docx | 1.0 | Phased development plan with task breakdown |

---

## 2. Architectural Principles

The architecture is governed by five principles applied consistently across all design decisions.

**Simplicity over premature optimisation.** The prototype uses the simplest solution that satisfies each requirement. Complexity is introduced only when a simpler approach has been proven insufficient.

**Abstraction at integration boundaries.** Every external dependency — OCR engines, AI APIs, file storage, email providers — is accessed through an abstract interface. Swapping implementations requires configuration changes, not code changes.

**Fail-safe defaults.** Processing pipelines default to routing documents to human review rather than making autonomous decisions when confidence is low or errors occur. Tax compliance errors carry significant business risk.

**Immutability for compliance data.** The audit log and all review actions are insert-only. No application-layer code may UPDATE or DELETE audit records.

**Stateless workers.** Celery workers hold no application state between tasks. All state is persisted to PostgreSQL or Redis. Workers can be restarted, scaled, or replaced at any time without data loss.

---

## 3. System Overview

### 3.1 High-Level Architecture

The platform is composed of six logical tiers that communicate through well-defined interfaces:

```
┌─────────────────────────────────────────────────────────────────┐
│                        BROWSER / CLIENT                         │
│              React + TypeScript + shadcn/ui SPA                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / REST + JSON
┌──────────────────────────▼──────────────────────────────────────┐
│                         API LAYER                               │
│                   FastAPI (Python 3.12)                         │
│         JWT validation · Request routing · Pydantic models      │
└──────┬────────────────────────────────────────┬─────────────────┘
       │ SQLAlchemy (async)                      │ Celery task dispatch
┌──────▼──────────┐                  ┌──────────▼──────────────────┐
│   DATA LAYER    │                  │      WORKER LAYER           │
│  PostgreSQL 16  │◄─────────────────│  Celery + Redis             │
│  JSONB · Audit  │  read/write      │  4 dedicated queues         │
└─────────────────┘                  └──────┬──────────────────────┘
                                            │
              ┌─────────────────────────────┼──────────────────────┐
              │                             │                      │
┌─────────────▼──────┐  ┌──────────────────▼───┐  ┌──────────────▼──────┐
│  DOCUMENT          │  │  AI / OCR LAYER       │  │  INTEGRATION        │
│  PROCESSING        │  │  Tier 1: pdfplumber   │  │  LAYER              │
│  LAYER             │  │  Tier 2: Azure DI     │  │  Microsoft Graph    │
│  Ingestion         │  │  Tier 3: OpenAI API   │  │  SendGrid           │
│  Validation        │  │  OpenCV preprocessing │  │  Supabase Auth      │
│  Storage           │  └───────────────────────┘  └─────────────────────┘
└────────────────────┘
```

### 3.2 Request Lifecycle

A typical document processing request follows this path:

1. User authenticates via Supabase Auth, receives JWT.
2. Frontend calls FastAPI endpoint with JWT in Authorization header.
3. FastAPI validates JWT, checks engagement membership, and processes the request.
4. For processing requests, FastAPI dispatches a Celery task and returns immediately with a job ID.
5. Celery worker picks up the task from Redis, executes the processing pipeline, and writes results to PostgreSQL.
6. Frontend polls a progress endpoint to track job completion.

---

## 4. Component Architecture

### 4.1 API Layer — FastAPI

#### Responsibility

The API layer is the sole entry point for all frontend requests. It handles authentication, request validation, business rule enforcement, and dispatches async tasks to the worker layer.

#### Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory, middleware, routers
│   ├── config.py                # Pydantic Settings from .env
│   ├── dependencies.py          # Shared FastAPI dependencies (auth, db session)
│   ├── routers/
│   │   ├── auth.py              # POST /auth/login, /auth/refresh
│   │   ├── engagements.py       # Engagement CRUD
│   │   ├── members.py           # Team membership
│   │   ├── folders.py           # OneDrive folder registration
│   │   ├── schema.py            # Output schema builder
│   │   ├── documents.py         # Document status, progress
│   │   ├── review.py            # HITL review queue and actions
│   │   ├── export.py            # Excel and CSV export
│   │   └── audit.py             # Audit log retrieval
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response schemas
│   └── services/                # Business logic (thin layer over DB + tasks)
```

#### Key API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `POST` | `/engagements` | Create engagement |
| `GET` | `/engagements` | List user's engagements |
| `GET` | `/engagements/{id}` | Get engagement detail |
| `POST` | `/engagements/{id}/activate` | Trigger ingestion pipeline |
| `POST` | `/engagements/{id}/members` | Add team member |
| `DELETE` | `/engagements/{id}/members/{uid}` | Remove team member |
| `POST` | `/engagements/{id}/folders` | Register OneDrive folder |
| `POST` | `/engagements/{id}/schema` | Save output schema |
| `GET` | `/engagements/{id}/progress` | Ingestion and processing progress |
| `GET` | `/engagements/{id}/review-queue` | HITL review queue |
| `POST` | `/engagements/{id}/documents/{doc_id}/review` | Submit reviewer action |
| `GET` | `/engagements/{id}/audit-log` | Retrieve audit log |
| `GET` | `/engagements/{id}/export` | Export results (xlsx or csv) |
| `PATCH` | `/engagements/{id}/threshold` | Update confidence threshold |

#### Middleware Stack

```python
app = FastAPI()

# Applied in order on every request
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS)
app.add_middleware(TrustedHostMiddleware)
app.add_middleware(RequestLoggingMiddleware)   # logs method, path, duration
app.add_middleware(AuthenticationMiddleware)   # JWT validation
```

---

### 4.2 Task Queue — Celery + Redis

#### Responsibility

All document processing is asynchronous. Celery workers execute the processing pipeline stages in the background, independent of the API request lifecycle. Redis serves as both the message broker (task dispatch) and the result backend (task state).

#### Queue Architecture

Four dedicated queues isolate pipeline stages. Each queue has its own worker pool sized for its performance characteristics:

| Queue | Purpose | Worker Type | Concurrency |
|---|---|---|---|
| `ingestion` | OneDrive listing and document download | Gevent (I/O bound) | 20 |
| `extraction` | OCR + AI extraction per document | Gevent (I/O bound) | 100 |
| `routing` | Confidence scoring and status assignment | Prefork (CPU light) | 8 |
| `notification` | Email dispatch on engagement completion | Gevent (I/O bound) | 4 |

#### Worker Configuration

```python
# celery_app.py
from celery import Celery

celery_app = Celery("taxautomation")

celery_app.config_from_object({
    "broker_url": settings.REDIS_URL,
    "result_backend": settings.REDIS_URL,
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "task_acks_late": True,           # task acknowledged only after completion
    "task_reject_on_worker_lost": True,  # requeue if worker crashes mid-task
    "worker_prefetch_multiplier": 1,  # one task per worker at a time
    "task_routes": {
        "tasks.ingestion.*": {"queue": "ingestion"},
        "tasks.extraction.*": {"queue": "extraction"},
        "tasks.routing.*": {"queue": "routing"},
        "tasks.notification.*": {"queue": "notification"},
    }
})
```

#### Task Chain

When an engagement is activated, a Celery chain is constructed that passes outputs between stages:

```python
from celery import chain, group

def activate_engagement(engagement_id: str):
    pipeline = chain(
        tasks.ingestion.list_documents.s(engagement_id),
        tasks.ingestion.download_documents.s(),
        group(
            tasks.extraction.extract_document.s(doc_id)
            for doc_id in queued_document_ids
        ),
        tasks.routing.route_all.s(engagement_id),
        tasks.notification.notify_on_completion.s(engagement_id),
    )
    pipeline.apply_async()
```

---

### 4.3 Document Processing Pipeline

#### Stage 1: Document Listing

The ingestion worker authenticates with Microsoft Graph API using the stored MSAL refresh token for the engagement's connected Microsoft account. It lists all files recursively in each registered OneDrive folder and returns file metadata.

```python
async def list_onedrive_documents(engagement_id: str) -> list[DocumentMetadata]:
    token = await msal_client.acquire_token_silent(engagement_id)
    folders = await db.get_engagement_folders(engagement_id)
    documents = []
    for folder in folders:
        items = await graph_client.list_folder_contents(
            folder.path, token, recursive=True
        )
        documents.extend(items)
    return documents
```

#### Stage 2: Format Validation

Each listed file is validated against the supported format list: PDF, TIFF, JPEG, PNG. Unsupported files are recorded with status `rejected` and a human-readable rejection reason. Zero-byte and corrupt files are also rejected at this stage.

```python
SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "image/tiff": "tiff",
    "image/jpeg": "jpeg",
    "image/png": "png",
}

def validate_document(file_metadata: DocumentMetadata) -> ValidationResult:
    if file_metadata.mime_type not in SUPPORTED_MIME_TYPES:
        return ValidationResult.rejected(f"Unsupported format: {file_metadata.mime_type}")
    if file_metadata.size_bytes == 0:
        return ValidationResult.rejected("Empty file")
    return ValidationResult.accepted()
```

#### Stage 3: Download and Storage

Valid documents are downloaded from OneDrive via Microsoft Graph API and written to the local filesystem under `/storage/{engagement_id}/{document_id}.{ext}`. A database record is created for each document with its OneDrive item ID, local path, source URL, and initial status.

#### Stage 4: Queue Population

After download, each document ID is pushed onto the `extraction` Celery queue. Document status is updated to `queued`. An engagement-level cap of 50,000 documents is enforced; documents beyond the cap are logged and skipped.

#### Document Status Lifecycle

```
discovered → validated → downloaded → queued → extracting
                                                    ↓
                                           extraction_failed (terminal)
                                                    ↓
                                              auto_approved (terminal)
                                                    ↓
                                           pending_review
                                                    ↓
                              confirmed / corrected / rejected (terminal)
```

---

### 4.4 OCR Tier System

The OCR layer uses a three-tier cascade. Each tier is attempted in order; if the result meets the confidence threshold for that tier, processing stops and the result is passed to the routing engine. Only documents that do not meet the threshold at an earlier tier progress to the next.

#### Architecture

```python
class OCRBackend(ABC):
    @abstractmethod
    async def extract(self, document: Document) -> OCRResult:
        """Returns extracted text, field values, and confidence score."""
        pass

class PdfPlumberBackend(OCRBackend):
    """Tier 1: Native digital PDF extraction. Free, instant, highest accuracy
    on clean PDFs. Returns confidence 1.0 for native-text PDFs."""
    pass

class AzureDocumentIntelligenceBackend(OCRBackend):
    """Tier 2: Azure DI prebuilt invoice model. Handles scanned PDFs,
    images, and complex layouts. Returns field-level confidence scores."""
    pass

class OpenAIBackend(OCRBackend):
    """Tier 3: LLM-based extraction with dynamic prompt built from the
    engagement output schema. Fallback for ambiguous or non-standard documents."""
    pass
```

#### Tier Routing Logic

```python
async def process_document(document: Document, schema: OutputSchema) -> ExtractionResult:

    # Tier 1 — pdfplumber (native PDFs only, free, no rate limits)
    if document.format == "pdf" and await is_native_pdf(document):
        result = await PdfPlumberBackend().extract(document)
        if result.confidence >= 0.90:
            return result.with_method("pdfplumber")

    # Tier 2 — Azure Document Intelligence (structured docs, images, scans)
    result = await AzureDocumentIntelligenceBackend().extract(document)
    if result.confidence >= 0.80:
        return result.with_method("azure_di")

    # Tier 3 — OpenAI API (complex, ambiguous, or non-standard documents)
    result = await OpenAIBackend().extract(document, schema=schema)
    return result.with_method("openai")
```

#### Expected Tier Distribution

For a typical SUT invoice engagement:

| Tier | Document Type | Expected Volume | Cost |
|---|---|---|---|
| pdfplumber | Native digital PDFs | ~40% | Free |
| Azure Document Intelligence | Scanned PDFs, images, structured forms | ~45% | ~$1.50 / 1,000 pages |
| OpenAI API | Complex, non-standard, or ambiguous documents | ~15% | ~$0.15 / 1M tokens |

This distribution reduces OpenAI API calls by approximately 85% compared to routing all documents through the LLM, cutting both cost and rate limit exposure.

#### Image Pre-Processing with OpenCV

Before passing scanned documents or images to Azure DI or Tesseract, OpenCV applies a pre-processing chain to improve extraction accuracy:

```python
import cv2
import numpy as np

def preprocess_image(image_path: str) -> np.ndarray:
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)          # greyscale
    denoised = cv2.fastNlMeansDenoising(gray, h=10)       # noise removal
    _, binary = cv2.threshold(                             # binarisation
        denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    coords = np.column_stack(np.where(binary > 0))
    angle = cv2.minAreaRect(coords)[-1]                    # deskew
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = binary.shape
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(binary, M, (w, h))
```

---

### 4.5 AI Extraction Engine

#### Dynamic Prompt Construction

The OpenAI extraction prompt is constructed dynamically from the engagement's output schema. This allows a single extraction function to serve any field configuration without code changes.

```python
def build_extraction_prompt(schema: OutputSchema, ocr_text: str) -> list[dict]:
    fields_description = "\n".join([
        f"- {field.name} ({field.type}): {field.label}"
        for field in schema.fields
    ])

    system_prompt = f"""You are a tax document data extraction specialist.
Extract the following fields from the provided document text.
Return a valid JSON object with exactly these keys and a confidence score.

Fields to extract:
{fields_description}

Response format:
{{
    "fields": {{
        "field_name": "extracted_value_or_null",
        ...
    }},
    "confidence": <integer 0-100>,
    "reasoning": "<brief explanation of confidence rating>"
}}

Rules:
- Return null for any field not found in the document.
- Set confidence below 70 if any required field is missing or ambiguous.
- Never fabricate values. Return null if uncertain.
"""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Document text:\n\n{ocr_text}"}
    ]
```

#### OpenAI API Call

```python
async def extract_with_openai(
    document: Document,
    schema: OutputSchema,
    ocr_text: str
) -> ExtractionResult:
    messages = build_extraction_prompt(schema, ocr_text)

    response = await openai_client.chat.completions.create(
        model=settings.OPENAI_MODEL,       # gpt-4o-mini
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,                     # deterministic extraction
        max_tokens=1000,
    )

    data = json.loads(response.choices[0].message.content)
    return ExtractionResult(
        fields=data["fields"],
        confidence=data["confidence"] / 100,
        reasoning=data.get("reasoning"),
        method="openai",
        tokens_used=response.usage.total_tokens,
    )
```

#### Rate Limiting

```python
@celery_app.task(
    bind=True,
    rate_limit="500/m",        # 500 OpenAI calls per minute per worker pool
    max_retries=3,
    default_retry_delay=10,
)
def extract_document_openai(self, document_id: str):
    try:
        ...
    except openai.RateLimitError as e:
        raise self.retry(exc=e, countdown=30)
    except openai.APIError as e:
        raise self.retry(exc=e, countdown=10)
```

---

### 4.6 Confidence & Routing Engine

#### Confidence Score Calculation

Each OCR tier returns a confidence score on a 0.0–1.0 scale:

- **pdfplumber**: Returns 1.0 for native-text PDFs (text extracted directly from PDF structure). Returns lower scores for PDFs with complex layouts or encoding issues.
- **Azure Document Intelligence**: Returns field-level confidence scores from the DI model. The document-level confidence is the mean of all configured field confidences.
- **OpenAI**: Returns the model's self-assessed confidence from the JSON response (0–100, normalised to 0.0–1.0).

#### Routing Decision

```python
async def route_document(document_id: str, engagement_id: str):
    extraction = await db.get_extraction(document_id)
    engagement = await db.get_engagement(engagement_id)
    threshold = engagement.confidence_threshold / 100  # stored as 0–100 integer

    if extraction.confidence >= threshold:
        await db.update_document_status(document_id, "auto_approved")
    else:
        await db.update_document_status(document_id, "pending_review")

    await db.insert_routing_log(
        document_id=document_id,
        confidence=extraction.confidence,
        threshold=threshold,
        decision="auto_approved" if extraction.confidence >= threshold else "pending_review",
        timestamp=datetime.utcnow(),
    )
```

#### Completion Detection

After all documents in an engagement reach a terminal status, the engagement is marked complete and the notification task is triggered:

```python
async def check_engagement_completion(engagement_id: str):
    counts = await db.get_document_status_counts(engagement_id)
    terminal_statuses = {"auto_approved", "confirmed", "corrected", "rejected", "extraction_failed", "download_failed"}
    all_terminal = all(
        status in terminal_statuses
        for status in counts.keys()
    )
    if all_terminal:
        await db.update_engagement_status(engagement_id, "complete")
        tasks.notification.notify_team.delay(engagement_id)
```

---

### 4.7 Human-in-the-Loop Review

#### Review Queue

Documents with status `pending_review` are surfaced to assigned team members in the review interface. The queue is ordered by confidence score ascending so reviewers see the least-certain documents first.

```python
async def get_review_queue(engagement_id: str) -> list[ReviewQueueItem]:
    return await db.query("""
        SELECT d.id, d.filename, d.source_url, d.storage_path,
               e.fields, e.confidence, e.reasoning, e.method
        FROM documents d
        JOIN extractions e ON e.document_id = d.id
        WHERE d.engagement_id = :engagement_id
          AND d.status = 'pending_review'
        ORDER BY e.confidence ASC
    """, {"engagement_id": engagement_id})
```

#### Reviewer Actions

Three actions are available per document:

| Action | Effect | Status After |
|---|---|---|
| `confirm` | Accept AI-extracted values as-is | `confirmed` |
| `correct` | Override one or more field values | `corrected` |
| `reject` | Exclude document from output | `rejected` |

```python
async def submit_review_action(
    document_id: str,
    reviewer_id: str,
    action: Literal["confirm", "correct", "reject"],
    corrected_values: dict | None = None,
):
    async with db.transaction():
        # Update document status
        new_status = {
            "confirm": "confirmed",
            "correct": "corrected",
            "reject": "rejected",
        }[action]
        await db.update_document_status(document_id, new_status)

        # If correcting, update extraction record
        if action == "correct" and corrected_values:
            await db.update_extraction_fields(document_id, corrected_values)

        # Write immutable audit log entry
        await db.insert_review_log(
            document_id=document_id,
            reviewer_id=reviewer_id,
            action=action,
            corrected_values=corrected_values,
            timestamp=datetime.utcnow(),
        )
```

#### Audit Log Immutability

The `review_log` table is enforced as insert-only at two levels:

1. **Application layer**: No `UPDATE` or `DELETE` statements are issued against `review_log` anywhere in the codebase.
2. **Database layer**: A PostgreSQL trigger raises an exception on any `UPDATE` or `DELETE` attempt:

```sql
CREATE OR REPLACE FUNCTION prevent_review_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'review_log is immutable. Modifications are not permitted.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER enforce_review_log_immutability
    BEFORE UPDATE OR DELETE ON review_log
    FOR EACH ROW EXECUTE FUNCTION prevent_review_log_modification();
```

---

### 4.8 Notification Service

Email notifications are dispatched by a Celery task on the `notification` queue. The notification is sent to all team members assigned to the engagement using SendGrid's transactional email API.

```python
@celery_app.task(queue="notification", max_retries=3)
def notify_team_on_completion(engagement_id: str):
    engagement = db.get_engagement(engagement_id)
    members = db.get_engagement_members(engagement_id)
    stats = db.get_engagement_stats(engagement_id)

    for member in members:
        sendgrid_client.send(
            to=member.email,
            subject=f"TaxAutomation: {engagement.project_name} — Processing Complete",
            template_data={
                "engagement_name": engagement.project_name,
                "client_name": engagement.client_name,
                "tax_year": engagement.tax_year,
                "total_documents": stats.total,
                "auto_approved": stats.auto_approved,
                "reviewed": stats.reviewed,
                "rejected": stats.rejected,
                "portal_url": f"{settings.APP_URL}/engagements/{engagement_id}/results",
            }
        )
```

---

### 4.9 Export Service

Export is generated synchronously on-demand. For large engagements (>10,000 documents) the export is streamed to avoid memory exhaustion.

#### Excel Export

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

async def generate_excel_export(engagement_id: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Extraction Results"

    schema = await db.get_engagement_schema(engagement_id)
    system_columns = ["Confidence Score", "Review Status", "Reviewer",
                      "Review Timestamp", "Extraction Method", "Source Document"]

    # Header row with styling
    headers = [field.label for field in schema.fields] + system_columns
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E79")
        cell.alignment = Alignment(horizontal="center")
    ws.freeze_panes = "A2"

    # Data rows
    documents = await db.get_engagement_results(engagement_id)
    for row_idx, doc in enumerate(documents, 2):
        for col_idx, field in enumerate(schema.fields, 1):
            ws.cell(row=row_idx, column=col_idx,
                    value=doc.extracted_fields.get(field.name))
        offset = len(schema.fields) + 1
        ws.cell(row=row_idx, column=offset, value=doc.confidence_score)
        ws.cell(row=row_idx, column=offset+1, value=doc.status)
        ws.cell(row=row_idx, column=offset+2, value=doc.reviewer_name)
        ws.cell(row=row_idx, column=offset+3, value=doc.review_timestamp)
        ws.cell(row=row_idx, column=offset+4, value=doc.extraction_method)
        ws.cell(row=row_idx, column=offset+5, value=doc.source_url)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
```

#### CSV Export

```python
async def generate_csv_export(engagement_id: str) -> StreamingResponse:
    schema = await db.get_engagement_schema(engagement_id)

    async def generate():
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=get_column_names(schema))
        writer.writeheader()
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)

        async for doc in db.stream_engagement_results(engagement_id):
            writer.writerow(doc_to_row(doc, schema))
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)

    return StreamingResponse(generate(), media_type="text/csv")
```

---

### 4.10 Frontend Application

#### Application Structure

```
frontend/
├── src/
│   ├── main.tsx                     # App entry point
│   ├── App.tsx                      # Router and layout
│   ├── lib/
│   │   ├── api.ts                   # Axios client with JWT interceptor
│   │   ├── auth.ts                  # Supabase Auth helpers
│   │   └── queryClient.ts           # TanStack Query configuration
│   ├── pages/
│   │   ├── Login.tsx
│   │   ├── EngagementList.tsx       # FR-004
│   │   ├── EngagementCreate.tsx     # FR-001, FR-002, FR-005, FR-010
│   │   ├── EngagementDashboard.tsx  # FR-009 (progress)
│   │   ├── ReviewQueue.tsx          # FR-015, FR-016
│   │   └── Results.tsx              # FR-020, FR-021, FR-022
│   └── components/
│       ├── SchemaBuilder.tsx        # Drag-and-drop field definition
│       ├── DocumentViewer.tsx       # Inline PDF rendering (react-pdf)
│       ├── ReviewPanel.tsx          # Side-by-side review interface
│       ├── ResultsGrid.tsx          # Virtualised TanStack Table
│       └── ExportControls.tsx       # Excel/CSV download triggers
```

#### Authentication Flow

```typescript
// lib/api.ts — JWT interceptor
const apiClient = axios.create({ baseURL: import.meta.env.VITE_API_URL });

apiClient.interceptors.request.use(async (config) => {
    const session = await supabase.auth.getSession();
    if (session.data.session?.access_token) {
        config.headers.Authorization = `Bearer ${session.data.session.access_token}`;
    }
    return config;
});

// Auto-refresh on 401
apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            await supabase.auth.refreshSession();
            return apiClient(error.config);
        }
        return Promise.reject(error);
    }
);
```

#### Progress Polling

```typescript
// pages/EngagementDashboard.tsx
const { data: progress } = useQuery({
    queryKey: ["progress", engagementId],
    queryFn: () => api.get(`/engagements/${engagementId}/progress`),
    refetchInterval: (data) =>
        data?.status === "complete" ? false : 5000,  // poll every 5s until done
});
```

#### Virtualised Results Grid

TanStack Table with row virtualisation handles up to 50,000 rows without performance degradation by rendering only the rows currently in the viewport.

```typescript
// components/ResultsGrid.tsx
const { rows } = table.getRowModel();
const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => 40,
    overscan: 20,
});
```

---

## 5. Data Architecture

### 5.1 Database Schema

#### users

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       VARCHAR(255) UNIQUE NOT NULL,
    full_name   VARCHAR(255),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

#### engagements

```sql
CREATE TABLE engagements (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_name          VARCHAR(255) NOT NULL,
    client_id            VARCHAR(100) NOT NULL,
    tax_year             INTEGER NOT NULL,
    project_name         VARCHAR(255) NOT NULL,
    status               VARCHAR(50) NOT NULL DEFAULT 'draft',
    -- draft | active | processing | complete | error
    confidence_threshold INTEGER NOT NULL DEFAULT 85,
    output_schema        JSONB,
    -- [{"name": "sales_tax", "label": "Sales Tax Amount", "type": "currency"}, ...]
    created_by           UUID REFERENCES users(id),
    created_at           TIMESTAMPTZ DEFAULT NOW(),
    updated_at           TIMESTAMPTZ DEFAULT NOW()
);
```

#### engagement_members

```sql
CREATE TABLE engagement_members (
    engagement_id  UUID REFERENCES engagements(id) ON DELETE CASCADE,
    user_id        UUID REFERENCES users(id) ON DELETE CASCADE,
    role           VARCHAR(50) NOT NULL DEFAULT 'reviewer',
    -- reviewer | lead
    added_at       TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (engagement_id, user_id)
);
```

#### onedrive_folders

```sql
CREATE TABLE onedrive_folders (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engagement_id   UUID REFERENCES engagements(id) ON DELETE CASCADE,
    folder_path     TEXT NOT NULL,
    display_name    VARCHAR(255),
    microsoft_user  VARCHAR(255),    -- Microsoft account email
    registered_at   TIMESTAMPTZ DEFAULT NOW()
);
```

#### documents

```sql
CREATE TABLE documents (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    engagement_id    UUID REFERENCES engagements(id) ON DELETE CASCADE,
    filename         VARCHAR(500) NOT NULL,
    format           VARCHAR(10) NOT NULL,       -- pdf | tiff | jpeg | png
    storage_path     TEXT,                        -- local filesystem path
    source_url       TEXT,                        -- OneDrive item URL
    onedrive_item_id VARCHAR(255),
    status           VARCHAR(50) NOT NULL DEFAULT 'discovered',
    rejection_reason TEXT,
    file_size_bytes  BIGINT,
    discovered_at    TIMESTAMPTZ DEFAULT NOW(),
    processed_at     TIMESTAMPTZ
);

CREATE INDEX idx_documents_engagement_status
    ON documents(engagement_id, status);
```

#### extractions

```sql
CREATE TABLE extractions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID REFERENCES documents(id) ON DELETE CASCADE,
    engagement_id       UUID REFERENCES engagements(id) ON DELETE CASCADE,
    fields              JSONB NOT NULL,
    -- {"sales_tax": "1245.00", "date": "2024-03-15", "jurisdiction": "CA", ...}
    confidence          NUMERIC(5,4) NOT NULL,    -- 0.0000 to 1.0000
    reasoning           TEXT,
    extraction_method   VARCHAR(50) NOT NULL,     -- pdfplumber | azure_di | openai
    tokens_used         INTEGER,
    extracted_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_extractions_document
    ON extractions(document_id);
```

#### review_log

```sql
CREATE TABLE review_log (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id       UUID REFERENCES documents(id),
    engagement_id     UUID REFERENCES engagements(id),
    reviewer_id       UUID REFERENCES users(id),
    action            VARCHAR(20) NOT NULL,    -- confirm | correct | reject
    corrected_values  JSONB,                   -- only populated for 'correct'
    confidence_at_review  NUMERIC(5,4),        -- snapshot of confidence when reviewed
    reviewed_at       TIMESTAMPTZ DEFAULT NOW()
    -- NO updated_at. This table is insert-only.
);

-- Immutability enforcement
CREATE TRIGGER enforce_review_log_immutability
    BEFORE UPDATE OR DELETE ON review_log
    FOR EACH ROW EXECUTE FUNCTION prevent_review_log_modification();
```

#### routing_log

```sql
CREATE TABLE routing_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID REFERENCES documents(id),
    engagement_id   UUID REFERENCES engagements(id),
    confidence      NUMERIC(5,4) NOT NULL,
    threshold       NUMERIC(5,4) NOT NULL,
    decision        VARCHAR(30) NOT NULL,    -- auto_approved | pending_review
    routed_at       TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 5.2 Data Flow

```
OneDrive Folder
      │
      │  Microsoft Graph API (list + download)
      ▼
 /storage/{engagement_id}/{document_id}.{ext}
      │
      │  OCR Tier 1 (pdfplumber) — native PDFs
      │  OCR Tier 2 (Azure DI)   — scanned/images
      │  OCR Tier 3 (OpenAI)     — complex/ambiguous
      ▼
extractions table
 { fields: JSONB, confidence: float, method: string }
      │
      │  Routing engine
      ▼
documents.status = 'auto_approved' OR 'pending_review'
      │
      │  Reviewer action (if pending_review)
      ▼
review_log (immutable)
documents.status = 'confirmed' | 'corrected' | 'rejected'
      │
      │  Export service
      ▼
 .xlsx / .csv file download
```

---

### 5.3 Storage Architecture

#### Prototype (Local Filesystem)

```
/storage/
├── {engagement_id_1}/
│   ├── {document_id_1}.pdf
│   ├── {document_id_2}.tiff
│   └── {document_id_3}.png
└── {engagement_id_2}/
    └── ...
```

#### Storage Abstraction Interface

```python
class StorageBackend(ABC):
    @abstractmethod
    async def write(self, path: str, content: bytes) -> str:
        """Write content and return the storage path."""
        pass

    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Read content from storage path."""
        pass

    @abstractmethod
    async def get_url(self, path: str) -> str:
        """Return a URL suitable for inline rendering."""
        pass

class LocalStorageBackend(StorageBackend):
    """Prototype implementation. Writes to local filesystem."""
    pass

class AzureBlobStorageBackend(StorageBackend):
    """Production implementation. Writes to Azure Blob Storage."""
    pass
```

Switching from local to Azure Blob Storage in production requires only a `.env` change: `STORAGE_BACKEND=azure_blob`.

---

## 6. Integration Architecture

### 6.1 Microsoft Graph API / OneDrive

**Purpose**: List and download documents from user-configured OneDrive folders.

**Authentication**: OAuth 2.0 Authorization Code Flow via MSAL. The user completes the OAuth flow in the browser; the backend exchanges the authorization code for access and refresh tokens. Refresh tokens are stored encrypted in the database per user.

**Key API calls**:

```python
# List folder contents
GET https://graph.microsoft.com/v1.0/me/drive/root:/{folder_path}:/children

# Download file content
GET https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content

# Get file metadata
GET https://graph.microsoft.com/v1.0/me/drive/items/{item_id}
```

**Token refresh**:

```python
async def get_valid_token(user_id: str) -> str:
    token_data = await db.get_user_microsoft_token(user_id)
    result = msal_app.acquire_token_by_refresh_token(
        refresh_token=token_data.refresh_token,
        scopes=["Files.Read", "offline_access"],
    )
    if "access_token" in result:
        await db.update_user_microsoft_token(user_id, result)
        return result["access_token"]
    raise AuthenticationError("Microsoft token refresh failed")
```

---

### 6.2 OpenAI API

**Purpose**: Tier 3 AI extraction for documents that do not meet confidence thresholds at Tiers 1 or 2.

**Configuration**:

```python
openai_client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    timeout=30.0,
    max_retries=0,    # retries handled by Celery
)
```

**Model**: `gpt-4o-mini` for prototype (cost-efficient). `gpt-4o` available as a configuration override for production validation runs.

**Rate limit strategy**: Celery `rate_limit="500/m"` on the extraction task combined with automatic retry on `RateLimitError` with a 30-second backoff.

---

### 6.3 Azure Document Intelligence

**Purpose**: Tier 2 OCR for scanned documents, image-based PDFs, and structured forms.

**Model**: `prebuilt-invoice` for standard invoice processing. Falls back to `prebuilt-document` for non-invoice tax documents.

```python
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

di_client = DocumentIntelligenceClient(
    endpoint=settings.AZURE_DI_ENDPOINT,
    credential=AzureKeyCredential(settings.AZURE_DI_KEY),
)

async def extract_with_azure_di(document_path: str) -> AzureDIResult:
    with open(document_path, "rb") as f:
        poller = di_client.begin_analyze_document(
            "prebuilt-invoice",
            analyze_request=f,
            content_type="application/octet-stream",
        )
    result = poller.result()
    return map_di_result_to_extraction(result)
```

**Cost**: Approximately $1.50 per 1,000 pages at standard tier. Free tier covers 500 pages per month, which is sufficient for prototype validation runs.

---

### 6.4 SendGrid / SMTP

**Purpose**: Transactional email for engagement completion notifications.

**Configuration**: SendGrid preferred. Falls back to any SMTP provider via `aiosmtplib` by changing `EMAIL_PROVIDER=smtp` in `.env`.

```python
class EmailBackend(ABC):
    @abstractmethod
    async def send(self, to: str, subject: str, template_data: dict): pass

class SendGridBackend(EmailBackend):
    pass

class SMTPBackend(EmailBackend):
    pass
```

---

### 6.5 Supabase Auth

**Purpose**: User authentication and JWT issuance.

**Flow**:

1. User submits email/password to Supabase Auth via the frontend SDK.
2. Supabase returns a JWT access token (15-minute expiry) and refresh token.
3. Frontend includes the access token in every API request header.
4. FastAPI validates the token against the Supabase JWT secret.
5. Frontend automatically refreshes the token before expiry.

```python
# FastAPI JWT validation dependency
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        user_id = payload.get("sub")
        return await db.get_user(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

---

## 7. Concurrency & Parallelism

### 7.1 Worker Pool Configuration

Each queue runs a dedicated worker container with a pool type matched to its workload:

| Queue | Pool Type | Concurrency | Rationale |
|---|---|---|---|
| `ingestion` | gevent | 20 | I/O bound — awaiting Graph API responses |
| `extraction` | gevent | 100 | I/O bound — awaiting OCR and OpenAI responses |
| `routing` | prefork | 8 | CPU light — simple threshold comparison |
| `notification` | gevent | 4 | I/O bound — awaiting SendGrid API |

Gevent is used for I/O-bound queues because each worker coroutine suspends during the API call, allowing other coroutines to run on the same thread. This enables 100 concurrent extraction calls per container with minimal memory overhead.

### 7.2 Throughput Estimate

With gevent pool at 100 concurrency on the extraction queue and an average OpenAI response time of 3 seconds:

```
Throughput = concurrency / avg_response_time_seconds × 60
           = 100 / 3 × 60
           = ~2,000 documents/minute per extraction worker container
```

For 30,000 documents with the three-tier cascade (only ~15% hitting OpenAI):

```
OpenAI documents  = 30,000 × 0.15 = 4,500
Time at 2,000/min = 4,500 / 2,000 = ~2.25 minutes for OpenAI tier
Azure DI tier     = 30,000 × 0.45 at higher throughput ≈ ~5 minutes
pdfplumber tier   = 30,000 × 0.40, near-instant ≈ <1 minute
Total estimate    = ~15–20 minutes end-to-end per engagement
```

This comfortably satisfies the non-functional requirement of completing 50,000 documents within a single working day.

### 7.3 Docker Compose Scaling

```bash
# Scale extraction workers horizontally during high-volume processing
docker compose up --scale worker-extraction=3

# Monitor live throughput in Flower dashboard
open http://localhost:5555
```

---

## 8. Security Architecture

### 8.1 Authentication

All API endpoints except `/health` require a valid JWT. Tokens are validated on every request; no server-side session state is maintained.

### 8.2 Authorisation

Engagement-level data isolation is enforced via a reusable FastAPI dependency:

```python
async def get_engagement_or_403(
    engagement_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Engagement:
    engagement = await db.get_engagement(engagement_id)
    if not engagement:
        raise HTTPException(status_code=404)
    is_member = await db.is_engagement_member(engagement_id, current_user.id)
    is_admin = current_user.role == "admin"
    if not (is_member or is_admin):
        raise HTTPException(status_code=403)
    return engagement
```

### 8.3 Credential Storage

- **Microsoft refresh tokens**: Stored encrypted at rest using Fernet symmetric encryption. The encryption key is injected via environment variable and never stored in the database.
- **OpenAI API key**: Environment variable only. Never logged or returned in API responses.
- **Supabase credentials**: Environment variables only.

### 8.4 Data Isolation

Each engagement's documents are stored in a separate directory keyed by engagement UUID. Database queries always filter by `engagement_id` derived from the authenticated user's membership, preventing cross-engagement data access.

### 8.5 Transport Security

All external communication uses HTTPS/TLS. In production, the application sits behind a TLS-terminating reverse proxy (nginx or Azure Front Door). Internal Docker Compose service communication uses Docker's internal network, which is not exposed to the host.

---

## 9. Error Handling & Resilience

### 9.1 Retry Policy

| Failure Type | Retry Count | Backoff | Terminal State |
|---|---|---|---|
| Document download failure | 3 | Exponential (10s, 30s, 90s) | `download_failed` |
| OCR extraction failure | 3 | Exponential (10s, 30s, 90s) | `extraction_failed` |
| OpenAI rate limit | 3 | Fixed 30s | `extraction_failed` |
| Email notification failure | 3 | Exponential | logged, not terminal |

### 9.2 Task Acknowledgement

Celery is configured with `task_acks_late=True` and `task_reject_on_worker_lost=True`. Tasks are only acknowledged after successful completion. If a worker crashes mid-task, the task is requeued and retried by another worker.

### 9.3 Processing State Preservation

All document statuses are persisted to PostgreSQL atomically. If the entire system is restarted mid-engagement, no documents need to be reprocessed from scratch. The ingestion pipeline checks for existing document records before downloading and skips documents already in a post-discovery state.

### 9.4 Graceful Degradation

If Azure Document Intelligence is unavailable, the OCR tier system falls through directly to the OpenAI tier. If OpenAI is unavailable, the document is marked `extraction_failed` and retried later. The HITL review workflow continues to function for all documents that have already been processed.

---

## 10. Infrastructure & Deployment

### 10.1 Docker Compose Configuration

```yaml
version: "3.9"

services:
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./storage:/storage
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker-ingestion:
    build:
      context: ./backend
    env_file: .env
    depends_on: [db, redis]
    volumes:
      - ./storage:/storage
    command: >
      celery -A app.celery_app worker
      -Q ingestion
      --concurrency=20
      --pool=gevent
      --loglevel=info

  worker-extraction:
    build:
      context: ./backend
    env_file: .env
    depends_on: [db, redis]
    volumes:
      - ./storage:/storage
    command: >
      celery -A app.celery_app worker
      -Q extraction
      --concurrency=100
      --pool=gevent
      --loglevel=info
    deploy:
      replicas: 2

  worker-routing:
    build:
      context: ./backend
    env_file: .env
    depends_on: [db, redis]
    command: >
      celery -A app.celery_app worker
      -Q routing
      --concurrency=8
      --loglevel=info

  worker-notification:
    build:
      context: ./backend
    env_file: .env
    depends_on: [db, redis]
    command: >
      celery -A app.celery_app worker
      -Q notification
      --concurrency=4
      --pool=gevent
      --loglevel=info

  flower:
    image: mher/flower:2.0
    ports:
      - "5555:5555"
    env_file: .env
    depends_on: [redis]
    command: celery flower --broker=${REDIS_URL}

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: taxautomation
      POSTGRES_USER: taxuser
      POSTGRES_PASSWORD: taxpass
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U taxuser -d taxautomation"]
      interval: 5s
      timeout: 3s
      retries: 10

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    env_file: .env
    depends_on: [api]

volumes:
  pgdata:
```

### 10.2 Backend Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 10.3 Environment Configuration

```env
# Application
APP_ENV=development
APP_URL=http://localhost:3000
SECRET_KEY=replace-with-secure-random-string
CORS_ORIGINS=http://localhost:3000

# Database
DATABASE_URL=postgresql+asyncpg://taxuser:taxpass@db:5432/taxautomation

# Redis
REDIS_URL=redis://redis:6379/0

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Azure Document Intelligence
AZURE_DI_ENDPOINT=https://your-instance.cognitiveservices.azure.com/
AZURE_DI_KEY=...

# Microsoft Graph (OneDrive)
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
MICROSOFT_TENANT_ID=...

# Storage
STORAGE_BACKEND=local
STORAGE_PATH=/storage

# Email
EMAIL_PROVIDER=sendgrid         # sendgrid | smtp
SENDGRID_API_KEY=SG....
EMAIL_FROM=noreply@taxautomation.com

# Auth (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_JWT_SECRET=...

# OCR Tier configuration
OCR_TIER1_CONFIDENCE_THRESHOLD=0.90
OCR_TIER2_CONFIDENCE_THRESHOLD=0.80
```

---

## 11. Production Migration Path

The prototype is architected so that the transition to production requires configuration changes and infrastructure upgrades, not re-architecture or code rewrites.

| Component | Prototype | Production | Migration Effort |
|---|---|---|---|
| OCR Tier 1 | pdfplumber | pdfplumber (unchanged) | None |
| OCR Tier 2 | Azure Document Intelligence | Azure Document Intelligence (upgraded tier) | Configuration |
| OCR Tier 3 | OpenAI gpt-4o-mini | OpenAI gpt-4o | Configuration |
| File Storage | Local filesystem | Azure Blob Storage | Configuration |
| Task Queue | Celery + Redis (Docker) | Celery + Azure Cache for Redis | Configuration |
| Database | PostgreSQL (Docker) | Azure Database for PostgreSQL / Supabase | Migration script |
| Infrastructure | Docker Compose | Azure Container Apps | Deployment config |
| Auth | Supabase Auth | Azure AD / Entra ID SSO | Auth provider swap |
| Monitoring | Flower | Azure Monitor + Application Insights | Additive |

---

## 12. Document Control

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | February 2026 | Product Team | Initial architectural specification |
