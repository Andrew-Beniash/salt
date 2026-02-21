# TaxAutomation Platform — Development Plan

**Version 1.0 | February 2026**

---

## Table of Contents

1. [Overview](#1-overview)
2. [Phase Summary](#2-phase-summary)
3. [Phase 1 — Infrastructure & Data Foundation](#3-phase-1--infrastructure--data-foundation)
4. [Phase 2 — Engagement & Team Management](#4-phase-2--engagement--team-management)
5. [Phase 3 — Document Ingestion Pipeline](#5-phase-3--document-ingestion-pipeline)
6. [Phase 4 — AI Extraction & Routing Engine](#6-phase-4--ai-extraction--routing-engine)
7. [Phase 5 — Notifications, Export & Frontend Polish](#7-phase-5--notifications-export--frontend-polish)
8. [Acceptance Criteria Mapping](#8-acceptance-criteria-mapping)
9. [Complete Task Reference](#9-complete-task-reference)
10. [Document Control](#10-document-control)

---

## 1. Overview

This development plan translates the TaxAutomation Platform functional specification into a structured, phase-based build schedule. It defines every task required to deliver the initial prototype, maps each task to the relevant functional requirements, and states the gate condition each phase must satisfy before the next phase begins.

The plan is organised into five sequential phases across 18 development days. Each phase has a defined scope, discrete tasks with explicit acceptance criteria, and a blocking gate that prevents progression until the phase deliverables are verified.

### Development Principles

- **Infrastructure before logic.** No business logic is built until the environment, database, authentication, and task queue are verified working end-to-end.
- **Backend before frontend.** Each API endpoint is implemented and tested before the corresponding UI screen is built.
- **Gate conditions are blocking.** A phase is not considered complete until every gate condition passes. Partial completion does not unlock the next phase.
- **Each task maps to a requirement.** Every task references the functional requirement (FR) or specification section it satisfies.

---

## 2. Phase Summary

| # | Phase | Scope | Days | Tasks |
|---|---|---|---|---|
| 1 | Infrastructure & Data Foundation | Scaffold, Docker, database, auth, Celery | 1–3 | 8 |
| 2 | Engagement & Team Management | Engagement CRUD, team, folders, schema | 4–6 | 7 |
| 3 | Document Ingestion Pipeline | Graph API, download, queue, progress | 7–9 | 8 |
| 4 | AI Extraction & Routing Engine | OCR tiers, OpenAI, confidence, HITL | 10–14 | 10 |
| 5 | Notifications, Export & Frontend Polish | Email, Excel/CSV, full UI, E2E testing | 15–18 | 8 |
| | **Total** | | **18 days** | **41 tasks** |

---

## 3. Phase 1 — Infrastructure & Data Foundation

> **Days 1–3**

Phase 1 establishes the technical foundation on which all subsequent phases depend. No business logic is built in this phase. The goal is a running local environment with a validated database schema, working authentication, and a confirmed deployment pipeline. Nothing proceeds to Phase 2 until a developer can spin up the full stack with a single command and authenticate successfully.

---

### P1-T01 — Initialise project repository and folder structure

**Description:** Create a monorepo with three top-level directories: `/backend` (FastAPI application), `/frontend` (React application), and `/infra` (Docker Compose and deployment configuration). Initialise git, add `.gitignore` for Python and Node environments, create `README.md` with setup instructions, and add `.env.example` containing all required environment variable keys with placeholder values.

**Spec Reference:** TechStack §Infrastructure

**Acceptance Criteria:**
- Repository is initialised with the correct directory structure
- `.env.example` contains every key listed in the environment configuration section of the tech stack
- `README.md` includes local setup steps

---

### P1-T02 — Configure Docker Compose stack

**Description:** Define `docker-compose.yml` with six services: `api` (FastAPI), `worker-ingestion`, `worker-extraction`, `worker-routing`, `worker-notification`, `flower` (Celery monitor), `redis`, `db` (PostgreSQL), and `frontend` (React). Configure health checks on `db` and `redis`. Mount `./storage:/storage` volume on API and worker services. Verify all services start cleanly with `docker compose up --build`.

**Spec Reference:** TechStack §Infrastructure

**Acceptance Criteria:**
- `docker compose up --build` completes without errors
- All nine containers reach a healthy/running state
- `docker compose ps` shows no containers in exit or restart state

---

### P1-T03 — Configure environment variables

**Description:** Create `.env` file with all required configuration keys: `DATABASE_URL`, `REDIS_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, `MICROSOFT_TENANT_ID`, `AZURE_DI_ENDPOINT`, `AZURE_DI_KEY`, `STORAGE_BACKEND`, `STORAGE_PATH`, `EMAIL_PROVIDER`, `SENDGRID_API_KEY`, `EMAIL_FROM`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, `SECRET_KEY`, `APP_URL`, `CORS_ORIGINS`, `OCR_TIER1_CONFIDENCE_THRESHOLD`, `OCR_TIER2_CONFIDENCE_THRESHOLD`.

**Spec Reference:** TechStack §Environment Configuration

**Acceptance Criteria:**
- All environment variables load correctly into the FastAPI settings object via Pydantic Settings
- Application fails to start with a clear error message if any required variable is missing

---

### P1-T04 — Initialise FastAPI application

**Description:** Create FastAPI app entry point (`app/main.py`) with a `GET /health` endpoint returning `{"status": "ok", "version": "1.0.0"}`. Configure CORS middleware, trusted host middleware, and a global exception handler. Define the Pydantic Settings class in `app/config.py` consuming all environment variables. Structure the application with `routers/`, `models/`, `schemas/`, `services/`, and `repositories/` directories.

**Spec Reference:** TechStack §Backend, Architectural Specification §4.1

**Acceptance Criteria:**
- `GET /health` returns HTTP 200 with correct JSON body
- FastAPI auto-generated docs are accessible at `/api/docs`
- Missing required environment variables cause startup failure with a descriptive error

---

### P1-T05 — Define PostgreSQL database schema and migrations

**Description:** Create SQLAlchemy ORM models for all core tables: `users`, `engagements`, `engagement_members`, `onedrive_folders`, `documents`, `extractions`, `review_log`, `routing_log`. Create Alembic migration for the initial schema. Add database indexes on `documents(engagement_id, status)` and `extractions(document_id)`. Implement the PostgreSQL trigger that enforces immutability of the `review_log` table. Run the initial migration and verify all tables are created correctly.

**Spec Reference:** FR-001, FR-003, FR-026, FR-027, Architectural Specification §5.1

**Acceptance Criteria:**
- `alembic upgrade head` runs without errors
- All seven tables exist with the correct columns and types
- Inserting and querying basic records via SQLAlchemy succeeds
- Attempting an UPDATE or DELETE on `review_log` raises a database exception

---

### P1-T06 — Implement JWT authentication middleware

**Description:** Integrate Supabase Auth on the frontend using `supabase-js`. Implement JWT validation in FastAPI using `python-jose` as a reusable dependency (`get_current_user`). The dependency decodes the token, validates the signature against the Supabase JWT secret, and returns the authenticated user. Protect all non-health endpoints. Implement Axios request interceptor on the frontend to attach the JWT to every API request and auto-refresh on 401 responses.

**Spec Reference:** FR-003, Spec §3.3 Security

**Acceptance Criteria:**
- Unauthenticated requests to protected endpoints receive HTTP 401
- A valid Supabase JWT is accepted and the correct user object is returned
- An expired or tampered token is rejected with HTTP 401
- Token refresh works automatically on the frontend without the user re-logging in

---

### P1-T07 — Configure Celery worker and Redis broker

**Description:** Create `app/celery_app.py` with Redis as broker and result backend. Configure four named queues (`ingestion`, `extraction`, `routing`, `notification`) with task routing. Set `task_acks_late=True` and `task_reject_on_worker_lost=True`. Create a sample task in each queue. Verify tasks dispatch from the API, execute on the correct worker, and are visible in the Flower dashboard.

**Spec Reference:** TechStack §Task Queue, Architectural Specification §4.2

**Acceptance Criteria:**
- A test task dispatched to each queue executes on the correct worker container
- Task result and status are visible in Flower at `http://localhost:5555`
- Worker restart mid-task causes the task to be requeued and retried

---

### P1-T08 — Scaffold React frontend

**Description:** Initialise React 18 + TypeScript project in `/frontend` using Vite. Install and configure: `shadcn/ui`, Tailwind CSS, `@tanstack/react-table` v8, `@tanstack/react-query`, `react-router-dom`, `axios`, `react-pdf`, and `supabase-js`. Configure the Axios client with base URL from environment and JWT interceptor. Set up a routing skeleton with placeholder pages for: Login, EngagementList, EngagementCreate, EngagementDashboard, ReviewQueue, and Results. Implement the application shell layout with a sidebar and header.

**Spec Reference:** TechStack §Frontend

**Acceptance Criteria:**
- `npm run dev` starts the React application without errors
- All six routes render placeholder pages without console errors
- Axios client correctly reads the API base URL from the Vite environment variable

---

### Phase 1 Gate Conditions

- [ ] `docker compose up --build` starts all containers without errors
- [ ] `GET /health` returns HTTP 200
- [ ] All database migrations run successfully and all tables exist
- [ ] The immutability trigger on `review_log` is active and verified
- [ ] A test user can authenticate via Supabase and receive a JWT accepted by FastAPI
- [ ] A test Celery task queues and executes; result is visible in Flower

---

## 4. Phase 2 — Engagement & Team Management

> **Days 4–6**

Phase 2 delivers the first user-facing features. By the end of this phase a tax professional can create a fully configured engagement — with team members, OneDrive folders, and an output schema — ready for document processing.

---

### P2-T01 — Implement engagement CRUD API

**Description:** Build the engagement router with five endpoints: `POST /engagements` (create with client name, client ID, tax year, project name), `GET /engagements` (list all engagements for the authenticated user), `GET /engagements/{id}` (get detail), `PATCH /engagements/{id}` (update metadata if status is `draft`), `DELETE /engagements/{id}` (soft delete if status is `draft`). Enforce that only assigned members and admins can access a given engagement via the `get_engagement_or_403` dependency.

**Spec Reference:** FR-001, FR-003, FR-004, FR-005

**Acceptance Criteria:**
- Creating an engagement returns HTTP 201 with the correct response body
- A user can only retrieve engagements they are assigned to
- Attempting to access another user's engagement returns HTTP 403
- Updating a `processing` or `complete` engagement returns HTTP 409

---

### P2-T02 — Implement team membership API

**Description:** Build `POST /engagements/{id}/members` to add a team member by email (looks up user by email, creates membership record) and `DELETE /engagements/{id}/members/{user_id}` to remove a member. Only the engagement creator or an admin may add or remove members. Return the updated member list after each operation.

**Spec Reference:** FR-002, FR-003, FR-006

**Acceptance Criteria:**
- Adding a valid user email creates a membership record and returns the updated team list
- Adding a non-existent email returns HTTP 404 with a clear message
- Only the engagement creator or admin can modify membership; others receive HTTP 403
- Removing the last member from an engagement returns HTTP 400 (engagement must have at least one member)

---

### P2-T03 — Implement OneDrive folder registration API

**Description:** Build `POST /engagements/{id}/folders` to register an OneDrive folder path against an engagement. Store folder path, display name, and the Microsoft account email of the registering user. Build `DELETE /engagements/{id}/folders/{folder_id}` to remove a registered folder. Validate that the engagement is in `draft` status before allowing folder changes.

**Spec Reference:** FR-007

**Acceptance Criteria:**
- Registering a folder creates a record and returns the folder list
- Folders cannot be added to an engagement in `processing` or `complete` status
- At least one folder must remain; removing the last folder returns HTTP 400

---

### P2-T04 — Implement Microsoft Graph OAuth 2.0 flow

**Description:** Build the full OAuth 2.0 authorisation code flow using MSAL. `GET /auth/microsoft` redirects to the Microsoft OAuth endpoint with the required scopes (`Files.Read`, `offline_access`, `User.Read`). `GET /auth/microsoft/callback` exchanges the code for access and refresh tokens via MSAL and stores them encrypted in the `microsoft_tokens` table. Build a token refresh helper that automatically obtains a fresh access token using the stored refresh token before any Graph API call.

**Spec Reference:** FR-007, Spec §3.3 Security, Architectural Specification §6.1

**Acceptance Criteria:**
- The OAuth flow completes and tokens are stored encrypted in the database
- The token refresh helper returns a valid access token without user interaction
- Attempting to use an expired token automatically triggers a refresh
- Microsoft credentials are never returned in API responses or logged

---

### P2-T05 — Implement output schema builder API

**Description:** Build `POST /engagements/{id}/schema` to save the user-defined output schema as a JSONB array against the engagement. Each field in the array has: `name` (machine key), `label` (display name), and `type` (`text` | `currency` | `date` | `number`). Build `GET /engagements/{id}/schema` to retrieve the current schema. Validate that field names are unique within a schema and contain no special characters.

**Spec Reference:** FR-014

**Acceptance Criteria:**
- Saving a schema with five or more fields succeeds and is retrievable
- Duplicate field names in a schema return HTTP 422 with a validation error
- Schema cannot be modified once engagement status is `processing` or `complete`

---

### P2-T06 — Build engagement list and creation wizard UI

**Description:** Build the Engagement List screen displaying a table of all accessible engagements with columns for: client name, project name, tax year, status badge, document count, and created date. Implement a four-step creation wizard: Step 1 (client details form), Step 2 (team member search and assignment), Step 3 (OneDrive folder connection and folder picker), Step 4 (output schema definition). Navigate to the engagement dashboard on completion.

**Spec Reference:** FR-001, FR-002, FR-004, FR-007, FR-014

**Acceptance Criteria:**
- All four wizard steps render and validate correctly
- Attempting to proceed with missing required fields shows inline validation errors
- Completed wizard creates the engagement and redirects to the dashboard
- Engagement list shows correct status badges and refreshes when engagements are updated

---

### P2-T07 — Build output schema builder UI component

**Description:** Build a drag-and-drop field builder where users can add named output fields, set the field type from a dropdown (text, currency, date, number), reorder fields via drag-and-drop, and remove fields. Show a live preview of the output column order. Provide a set of suggested field templates for common SUT document types (invoice, receipt, exemption certificate) that pre-populate a sensible starting schema. Persist schema via the schema API.

**Spec Reference:** FR-014

**Acceptance Criteria:**
- Fields can be added, reordered by drag-and-drop, and deleted
- Saving an empty schema shows a validation error
- Field templates pre-populate the builder with the correct fields
- Schema preview accurately reflects the current field order and labels

---

### Phase 2 Gate Conditions

- [ ] A user can create an engagement with all required fields
- [ ] Team members can be added and removed
- [ ] At least one OneDrive folder can be registered per engagement
- [ ] An output schema with at least five fields can be saved and retrieved
- [ ] Only assigned team members can view or modify the engagement
- [ ] Microsoft OAuth flow completes successfully and tokens are stored

---

## 5. Phase 3 — Document Ingestion Pipeline

> **Days 7–9**

Phase 3 builds the automated document ingestion pipeline. When processing is activated, the system connects to OneDrive, retrieves all supported documents, validates their format, and queues them for extraction. All edge cases are handled at this phase.

---

### P3-T01 — Implement engagement activation endpoint

**Description:** Build `POST /engagements/{id}/activate`. Validate preconditions: at least one folder is registered, the output schema has at least one field, engagement status is `draft`. Set engagement status to `processing`, record `activated_at` timestamp, and dispatch the ingestion Celery task chain. Return `{"status": "processing"}` immediately without waiting for ingestion to begin.

**Spec Reference:** FR-013

**Acceptance Criteria:**
- Activation with missing folder or schema returns HTTP 400 with a specific error message
- Activating an already-active engagement returns HTTP 409
- On successful activation, the engagement status changes to `processing` and the ingestion task appears in Flower

---

### P3-T02 — Implement document listing via Microsoft Graph API

**Description:** Build the `ingestion.list_documents` Celery task. Authenticate using the stored MSAL token for the engagement's linked Microsoft account. Call Microsoft Graph API to list all files in each registered folder recursively. Return file metadata: OneDrive item ID, file name, MIME type, file size, download URL, and parent folder path. Create a `documents` record in the database for each discovered file with status `discovered`.

**Spec Reference:** FR-007, FR-009

**Acceptance Criteria:**
- All files in the configured folders are discovered and recorded in the documents table
- The task handles pagination from Microsoft Graph API for folders with more than 200 items
- Token refresh is triggered automatically if the access token has expired
- Graph API errors are caught, logged, and cause the task to retry

---

### P3-T03 — Implement document format validation and filtering

**Description:** For each discovered document, validate the MIME type against the supported list (PDF, TIFF, JPEG, PNG). Documents with unsupported MIME types, zero file size, or corrupt metadata are updated to status `rejected` with a human-readable `rejection_reason`. Valid documents are updated to status `validated`. Enforce the 50,000 document per engagement cap; documents beyond the cap are rejected with reason `"Engagement document limit exceeded"`.

**Spec Reference:** FR-008, FR-009, FR-011

**Acceptance Criteria:**
- TIFF, JPEG, PNG, and PDF files are correctly validated
- A Word document or Excel file is rejected with the correct reason
- Engagement cap is enforced; the 50,001st document is rejected
- Rejection reasons are descriptive and stored in the database

---

### P3-T04 — Implement document download and local storage

**Description:** Build the `ingestion.download_document` Celery task. Download the document content from OneDrive using the Graph API download URL. Write the content to `/storage/{engagement_id}/{document_id}.{ext}`. Update the document record with `storage_path`, `downloaded_at`, and status `downloaded`. Handle large files by streaming the download to disk rather than loading into memory.

**Spec Reference:** FR-008, Architectural Specification §5.3

**Acceptance Criteria:**
- Documents are written to the correct storage path with the correct file extension
- Files larger than 50MB are downloaded via streaming without memory errors
- The storage path is correctly recorded in the database
- Download errors update the document status to `download_failed` with the error detail

---

### P3-T05 — Implement download retry logic

**Description:** Configure the `download_document` task with `max_retries=3` and exponential backoff (10s, 30s, 90s). On final failure, set document status to `download_failed` and store the error detail in `error_detail`. Ensure failed downloads do not block other documents from processing — each document is an independent task.

**Spec Reference:** Spec §3.2 Reliability

**Acceptance Criteria:**
- A simulated network failure triggers automatic retry up to three times
- After three failures the document is marked `download_failed`
- Other documents in the same engagement continue processing during a retry sequence
- All retry attempts are visible in Flower

---

### P3-T06 — Implement queue population

**Description:** After each document is successfully downloaded, push its document ID onto the `extraction` Celery queue. Update document status to `queued`. Build the queue population to dispatch documents in batches of 100 to avoid overwhelming Redis with 50,000 simultaneous task messages.

**Spec Reference:** FR-009

**Acceptance Criteria:**
- Each downloaded document appears on the extraction queue in Flower
- Documents are dispatched in batches of 100
- Queue depth in Flower accurately reflects the number of pending extractions

---

### P3-T07 — Implement ingestion progress tracking API

**Description:** Build `GET /engagements/{id}/progress` returning a JSON object with counts for each document status: `discovered`, `validated`, `rejected`, `downloaded`, `queued`, `extracting`, `auto_approved`, `pending_review`, `confirmed`, `corrected`, `extraction_failed`, `download_failed`, plus `total` and `percent_complete`. Calculate `percent_complete` as the ratio of terminal-status documents to total documents.

**Spec Reference:** FR-012

**Acceptance Criteria:**
- Progress endpoint returns accurate counts matching the actual document table
- `percent_complete` updates correctly as documents move through pipeline stages
- Response time is under 500ms even for 50,000 document engagements

---

### P3-T08 — Build ingestion progress dashboard UI

**Description:** Build the Engagement Dashboard screen. Display a progress bar driven by `percent_complete`. Show individual count cards for each pipeline stage. Display a rejected documents panel listing file names and rejection reasons. Poll `GET /engagements/{id}/progress` every 5 seconds while engagement status is `processing`; stop polling when status is `complete`. Show an "Activate Processing" button in `draft` status that calls the activation endpoint.

**Spec Reference:** FR-012, FR-013

**Acceptance Criteria:**
- Progress bar and counts update live during processing without a page refresh
- Polling stops automatically when the engagement reaches `complete`
- Rejected documents are listed with their reasons
- The Activate button is disabled after activation and replaced with a status indicator

---

### Phase 3 Gate Conditions

- [ ] Activating an engagement triggers document retrieval from all linked OneDrive folders
- [ ] PDF, TIFF, JPEG, and PNG files are downloaded and stored correctly
- [ ] Unsupported file types are rejected with descriptive reasons
- [ ] Failed downloads are retried three times before being marked failed
- [ ] Progress is visible in the UI and updates in real time
- [ ] Documents appear on the extraction queue in Flower after download

---

## 6. Phase 4 — AI Extraction & Routing Engine

> **Days 10–14**

Phase 4 is the core intelligence layer. Each queued document passes through the three-tier OCR cascade, receives a confidence score, and is automatically routed to either auto-approval or the human review queue. Phase 4 also delivers the HITL review interface and the immutable audit log.

---

### P4-T01 — Implement OCR abstraction and pdfplumber backend (Tier 1)

**Description:** Define the abstract `OCRBackend` base class with `extract(document) -> OCRResult` method. `OCRResult` contains: `raw_text`, `fields`, `confidence` (0.0–1.0), `method`, and `page_count`. Implement `PdfPlumberBackend` for native digital PDFs. Extract text per page with layout awareness. Return confidence 1.0 for successfully extracted native-text PDFs. Return confidence below 0.90 for image-only or scanned PDFs detected by pdfplumber.

**Spec Reference:** FR-015, FR-016, Architectural Specification §4.4

**Acceptance Criteria:**
- Native digital PDF extracts clean text with confidence ≥ 0.90
- A scanned PDF (image only) returns confidence < 0.90 and escalates to Tier 2
- Extraction time for a native PDF is under 200ms

---

### P4-T02 — Implement Azure Document Intelligence backend (Tier 2)

**Description:** Implement `AzureDocumentIntelligenceBackend` using the Azure DI Python SDK. Call the `prebuilt-invoice` model for PDF and image documents. Map the Azure DI field names to the engagement output schema fields. Calculate document-level confidence as the mean of individual field confidences. Apply the OpenCV pre-processing chain (deskew, denoise, binarise) to image documents before passing to Azure DI.

**Spec Reference:** FR-015, FR-016, FR-020, Architectural Specification §4.4

**Acceptance Criteria:**
- A scanned invoice returns structured field values with confidence scores
- OpenCV pre-processing improves extraction on a deliberately skewed test image
- Azure DI confidence scores map correctly to the 0.0–1.0 normalised range
- Azure DI errors are caught and cause escalation to Tier 3 (not task failure)

---

### P4-T03 — Implement OpenAI extraction backend (Tier 3)

**Description:** Implement `OpenAIBackend` using the official Python SDK. Build the dynamic prompt from the engagement output schema. Call `gpt-4o-mini` with `response_format={"type": "json_object"}` and `temperature=0`. Parse the JSON response to extract field values and confidence score. Store `tokens_used` from the API response for cost tracking.

**Spec Reference:** FR-015, FR-016, FR-017, Architectural Specification §4.5

**Acceptance Criteria:**
- The prompt is dynamically constructed from any valid output schema
- The API returns a valid JSON object with all schema field keys
- A confidence score between 0 and 100 is returned in every response
- `tokens_used` is stored against the extraction record
- Invalid or malformed API responses are caught and cause the task to retry

---

### P4-T04 — Implement three-tier extraction Celery task

**Description:** Build the `extraction.extract_document` Celery task. Implement the cascade logic: try Tier 1 (pdfplumber) for PDFs — if confidence ≥ 0.90, store result and return; try Tier 2 (Azure DI) — if confidence ≥ 0.80, store result and return; try Tier 3 (OpenAI) — store result regardless of confidence. Store the extraction result in the `extractions` table. Update document status to `extracting` when the task begins. Configure `max_retries=3`, `rate_limit="500/m"`, and gevent pool.

**Spec Reference:** FR-015, FR-016, FR-017, FR-019, Spec §3.2

**Acceptance Criteria:**
- Documents meeting Tier 1 threshold never reach Tier 2 or Tier 3
- Documents meeting Tier 2 threshold never reach Tier 3
- All three tiers handle their respective document types correctly
- The `extraction_method` field in the database correctly records which tier processed each document
- Task retry on OpenAI `RateLimitError` waits 30 seconds before retrying

---

### P4-T05 — Implement confidence-based routing task

**Description:** Build the `routing.route_document` Celery task. Read the extracted confidence score and compare it against the engagement's `confidence_threshold` (default 85, stored as integer 0–100). Set document status to `auto_approved` if confidence × 100 ≥ threshold, or `pending_review` if below. Write a record to `routing_log` with the confidence, threshold, and routing decision. After routing each document, call the completion check.

**Spec Reference:** FR-021, FR-022, Architectural Specification §4.6

**Acceptance Criteria:**
- A document with confidence 0.92 and threshold 85 is auto-approved
- A document with confidence 0.72 and threshold 85 is routed to pending_review
- A routing_log entry is created for every document
- Changing the engagement threshold and re-running routing produces the correct new decisions

---

### P4-T06 — Implement configurable confidence threshold

**Description:** Build `PATCH /engagements/{id}/threshold` accepting `{"threshold": 75}` (integer 0–100). Validate range and update the engagement record. Only the engagement creator or admin may change the threshold. Changing the threshold after processing has started does not retroactively re-route already-processed documents; it applies only to documents processed after the change.

**Spec Reference:** FR-022

**Acceptance Criteria:**
- Threshold update within range 0–100 succeeds
- Values outside 0–100 return HTTP 422
- Non-admin, non-creator team members receive HTTP 403
- New threshold applies to documents routed after the update

---

### P4-T07 — Implement engagement completion detection

**Description:** Build the `routing.check_engagement_complete` task. After each document is routed, query the count of documents in non-terminal statuses for the engagement. Terminal statuses: `auto_approved`, `confirmed`, `corrected`, `rejected`, `extraction_failed`, `download_failed`. When the non-terminal count reaches zero, update engagement status to `complete`, record `completed_at`, and dispatch the notification task.

**Spec Reference:** FR-029

**Acceptance Criteria:**
- Engagement status changes to `complete` when all documents reach a terminal status
- `completed_at` is recorded accurately
- The notification task is dispatched exactly once
- Completion is not triggered if any documents remain in non-terminal status

---

### P4-T08 — Implement HITL review queue API

**Description:** Build `GET /engagements/{id}/review-queue` returning all documents with status `pending_review`, ordered by confidence score ascending. Each item includes: document ID, file name, storage path, source URL, extracted field values, confidence score, extraction reasoning (from OpenAI if available), and extraction method. Include pagination with `page` and `limit` query parameters.

**Spec Reference:** FR-023, FR-024

**Acceptance Criteria:**
- Review queue returns only `pending_review` documents for the engagement
- Results are ordered by confidence score ascending (least certain first)
- Pagination works correctly for large review queues
- All required fields are present in the response

---

### P4-T09 — Implement reviewer action API and audit log

**Description:** Build `POST /engagements/{id}/documents/{doc_id}/review` accepting `{"action": "confirm" | "correct" | "reject", "corrected_values": {...}}`. Within a database transaction: update document status to `confirmed`, `corrected`, or `rejected`; if action is `correct`, update `extractions.fields` with the corrected values; insert an immutable record into `review_log` with reviewer ID (from JWT), action, corrected values, confidence at time of review, and timestamp. Build `GET /engagements/{id}/audit-log` returning the full log ordered by `reviewed_at`.

**Spec Reference:** FR-025, FR-026, FR-027, FR-028

**Acceptance Criteria:**
- All three actions update the document status correctly
- Corrected values are stored in the extraction record and used in exports
- Every review action creates a review_log entry with reviewer identity and timestamp
- Attempting to review an already-reviewed document returns HTTP 409
- The audit log endpoint returns all entries in chronological order
- Attempting to modify or delete a review_log entry via the API or database raises an error

---

### P4-T10 — Build HITL review interface UI

**Description:** Build the Review Queue screen with a split-pane layout. Left panel: renders the source document inline using `react-pdf` for PDFs or an `<img>` tag for images. Right panel: displays each extracted field as a labelled, editable input pre-populated with the AI-extracted value. Show confidence score as a colour-coded badge (red < 60%, amber 60–84%, green ≥ 85%). Provide Confirm, Correct, and Reject action buttons. After each action, automatically advance to the next document in the queue. Show queue position (e.g. "12 of 47 remaining").

**Spec Reference:** FR-023, FR-024, FR-025

**Acceptance Criteria:**
- PDFs render inline without a download prompt
- Field inputs are pre-populated with AI values and editable
- Confirm, Correct (saves edits), and Reject submit the correct API payload
- Queue position updates correctly after each action
- Empty review queue shows a "Review complete" confirmation screen

---

### Phase 4 Gate Conditions

- [ ] OCR extracts usable text from PDF, TIFF, JPEG, and PNG documents
- [ ] Three-tier cascade correctly routes documents to the appropriate tier
- [ ] Every extraction record has a confidence score and extraction method
- [ ] Documents above threshold are auto-approved; documents below are pending review
- [ ] Reviewer can confirm, correct, and reject via the review UI
- [ ] Every review action is logged with reviewer identity and timestamp
- [ ] 95%+ field-level accuracy achieved on a sample of 100 clean documents

---

## 7. Phase 5 — Notifications, Export & Frontend Polish

> **Days 15–18**

Phase 5 completes the prototype by delivering email notifications, structured data exports, and full frontend integration. End-to-end testing validates all acceptance criteria from the specification.

---

### P5-T01 — Implement email notification task

**Description:** Build the `notification.notify_team` Celery task. Retrieve all team members and their email addresses. Retrieve engagement completion statistics. Send an email to each team member via SendGrid containing: engagement name, client name, tax year, total documents, auto-approved count, reviewed count, rejected count, failed count, and a direct link to the results screen. Handle SendGrid API errors with retry (max 3 attempts).

**Spec Reference:** FR-029, FR-030

**Acceptance Criteria:**
- Each team member receives exactly one notification email on engagement completion
- Email contains all required fields from FR-030
- The results link is correctly constructed from `APP_URL` and engagement ID
- SendGrid delivery failure triggers retry; final failure is logged without affecting engagement status

---

### P5-T02 — Implement Excel export

**Description:** Build `GET /engagements/{id}/export?format=xlsx`. Use `openpyxl` to generate one row per document. Column order: all output schema fields in schema-defined order, then system columns: Confidence Score, Review Status, Reviewer, Review Timestamp, Extraction Method, Source Document Link. Apply header formatting (bold white text on dark blue background). Freeze the header row. Auto-size column widths. Return as a file download with filename `{engagement_name}_{date}.xlsx`.

**Spec Reference:** FR-031, FR-033

**Acceptance Criteria:**
- Excel file opens correctly in Microsoft Excel and Google Sheets
- All configured schema fields are present as columns in schema order
- All system columns are present
- Corrected field values (not original AI values) appear for `corrected` documents
- Confidence score is formatted as a percentage
- Header row is frozen and visible when scrolling

---

### P5-T03 — Implement CSV export

**Description:** Build `GET /engagements/{id}/export?format=csv`. Stream the CSV response using Python's `csv` module to avoid loading all rows into memory for large engagements. Column order is identical to the Excel export. Return as a streaming file download with filename `{engagement_name}_{date}.csv`. Use UTF-8 encoding with BOM for correct Excel compatibility when opened directly.

**Spec Reference:** FR-032, FR-033

**Acceptance Criteria:**
- CSV file opens correctly in Excel with correct column detection
- All columns present in the same order as the Excel export
- File is streamed — memory usage does not scale with row count
- UTF-8 BOM is included for Excel compatibility

---

### P5-T04 — Build results grid UI

**Description:** Build the Results screen using TanStack Table with row virtualisation. Display all output schema fields as columns plus system columns: Confidence Score (colour-coded badge), Review Status (badge), Reviewer, and Source Document Link (clickable). Implement column sorting (click header), text search (filters across all fields), and column visibility toggle. Show aggregate statistics above the grid: total documents, auto-approved %, reviewed %, rejected %.

**Spec Reference:** FR-034

**Acceptance Criteria:**
- Grid renders 50,000 rows without scroll jank (virtual rendering verified)
- Column sorting and text search work correctly
- Confidence score badges use correct colour coding
- Source document links open the OneDrive document in a new tab

---

### P5-T05 — Build export controls UI

**Description:** Add "Export to Excel" and "Export to CSV" buttons to the Results screen toolbar. Clicking either button calls the corresponding export endpoint and initiates a browser file download. Show a loading spinner during export generation. Display a toast notification on successful download. Disable export buttons while a download is in progress.

**Spec Reference:** FR-031, FR-032

**Acceptance Criteria:**
- Both export buttons trigger file downloads with the correct filenames
- Loading spinner is shown during export generation
- Buttons are disabled while a download is in progress
- Toast notification confirms successful download

---

### P5-T06 — Frontend navigation and application shell integration

**Description:** Connect all screens into the complete application flow using `react-router-dom`: Login → Engagement List → Engagement Dashboard → Review Queue → Results. Implement a persistent left sidebar showing navigation links and the current user's name. Add a logout control. Implement breadcrumb navigation on detail screens. Protect all routes with an auth guard that redirects unauthenticated users to Login.

**Spec Reference:** All FR

**Acceptance Criteria:**
- Unauthenticated users are redirected to the Login screen for all protected routes
- Sidebar navigation links are active and correctly highlighted for the current route
- Logout clears the Supabase session and redirects to Login
- Breadcrumb navigation shows correct engagement name and context

---

### P5-T07 — Error handling and loading states

**Description:** Implement consistent error handling across all UI screens. Every API call should show a loading skeleton or spinner while pending, a descriptive inline error message on failure (not just "Something went wrong"), and a retry action where appropriate. Implement a global error boundary to catch unhandled React errors. Add empty state illustrations for: no engagements, no documents, empty review queue, no results.

**Spec Reference:** All FR

**Acceptance Criteria:**
- Every screen that loads data shows a loading state before data arrives
- API errors show the error message from the server response where available
- The empty review queue shows a "All documents reviewed" confirmation state
- Global error boundary prevents unhandled errors from crashing the entire application

---

### P5-T08 — End-to-end acceptance testing

**Description:** Execute a full end-to-end test run against all seven acceptance criteria from the functional specification using a real batch of 500 mixed-format documents. Document results for each criterion. For any criterion not met, open a defect, assign it to the appropriate phase, and re-test after resolution. Produce a written sign-off document confirming all criteria are satisfied before presenting to business users.

**Spec Reference:** Spec §6 Acceptance Criteria (AC-001 through AC-007)

**Acceptance Criteria:**
- AC-001: Engagement creation, team, folders, and schema — verified
- AC-002: 500 documents processed with 95%+ field accuracy — verified and measured
- AC-003: Review queue, reviewer actions, and audit log — verified
- AC-004: Email notification received by all team members — verified
- AC-005: Excel and CSV exports with all required columns — verified
- AC-006: Three-tier OCR routing verified via extraction_method column — verified
- AC-007: Audit log immutability — verified by attempting direct modification

---

### Phase 5 Gate Conditions — Prototype Complete

- [ ] Email notification received by team members on engagement completion
- [ ] Excel and CSV exports contain all configured fields and system columns
- [ ] Results grid renders 50,000 rows with virtual scrolling
- [ ] All seven acceptance criteria from the functional specification are satisfied
- [ ] Full application flow is navigable end-to-end without errors
- [ ] Sign-off document is produced confirming prototype readiness for business user presentation

---

## 8. Acceptance Criteria Mapping

| Criteria | Delivered By | Verification |
|---|---|---|
| **AC-001** Engagement creation, team, folders, schema | P2-T01, P2-T02, P2-T03, P2-T04, P2-T05, P2-T06, P2-T07 | Functional walkthrough |
| **AC-002** 500 documents, 95%+ accuracy | P3-T01–T08, P4-T01–T05 | Batch processing test |
| **AC-003** Review queue, actions, audit log | P4-T05, P4-T07, P4-T08, P4-T09, P4-T10 | Review workflow walkthrough |
| **AC-004** Email notification on completion | P4-T07, P5-T01 | Email delivery test |
| **AC-005** Excel and CSV exports | P5-T02, P5-T03, P5-T04, P5-T05 | Export verification |
| **AC-006** Three-tier OCR cascade | P4-T01, P4-T02, P4-T03, P4-T04 | Pipeline inspection test |
| **AC-007** Audit log immutability | P1-T05, P4-T09 | Audit log integrity test |

---

## 9. Complete Task Reference

| Task ID | Phase | Task Name | FR Reference |
|---|---|---|---|
| P1-T01 | Phase 1 | Initialise project repository and folder structure | TechStack §Infrastructure |
| P1-T02 | Phase 1 | Configure Docker Compose stack | TechStack §Infrastructure |
| P1-T03 | Phase 1 | Configure environment variables | TechStack §Environment |
| P1-T04 | Phase 1 | Initialise FastAPI application | TechStack §Backend |
| P1-T05 | Phase 1 | Define PostgreSQL database schema and migrations | FR-001, FR-003, FR-026, FR-027 |
| P1-T06 | Phase 1 | Implement JWT authentication middleware | FR-003, Spec §3.3 |
| P1-T07 | Phase 1 | Configure Celery worker and Redis broker | TechStack §Task Queue |
| P1-T08 | Phase 1 | Scaffold React frontend | TechStack §Frontend |
| P2-T01 | Phase 2 | Implement engagement CRUD API | FR-001, FR-003, FR-004, FR-005 |
| P2-T02 | Phase 2 | Implement team membership API | FR-002, FR-003, FR-006 |
| P2-T03 | Phase 2 | Implement OneDrive folder registration API | FR-007 |
| P2-T04 | Phase 2 | Implement Microsoft Graph OAuth 2.0 flow | FR-007, Spec §3.3 |
| P2-T05 | Phase 2 | Implement output schema builder API | FR-014 |
| P2-T06 | Phase 2 | Build engagement list and creation wizard UI | FR-001, FR-002, FR-004, FR-007, FR-014 |
| P2-T07 | Phase 2 | Build output schema builder UI component | FR-014 |
| P3-T01 | Phase 3 | Implement engagement activation endpoint | FR-013 |
| P3-T02 | Phase 3 | Implement document listing via Microsoft Graph API | FR-007, FR-009 |
| P3-T03 | Phase 3 | Implement document format validation and filtering | FR-008, FR-009, FR-011 |
| P3-T04 | Phase 3 | Implement document download and local storage | FR-008 |
| P3-T05 | Phase 3 | Implement download retry logic | Spec §3.2 |
| P3-T06 | Phase 3 | Implement queue population | FR-009 |
| P3-T07 | Phase 3 | Implement ingestion progress tracking API | FR-012 |
| P3-T08 | Phase 3 | Build ingestion progress dashboard UI | FR-012, FR-013 |
| P4-T01 | Phase 4 | Implement OCR abstraction and pdfplumber backend | FR-015, FR-016 |
| P4-T02 | Phase 4 | Implement Azure Document Intelligence backend | FR-015, FR-016, FR-020 |
| P4-T03 | Phase 4 | Implement OpenAI extraction backend | FR-015, FR-016, FR-017 |
| P4-T04 | Phase 4 | Implement three-tier extraction Celery task | FR-015, FR-016, FR-017, FR-019 |
| P4-T05 | Phase 4 | Implement confidence-based routing task | FR-021, FR-022 |
| P4-T06 | Phase 4 | Implement configurable confidence threshold | FR-022 |
| P4-T07 | Phase 4 | Implement engagement completion detection | FR-029 |
| P4-T08 | Phase 4 | Implement HITL review queue API | FR-023, FR-024 |
| P4-T09 | Phase 4 | Implement reviewer action API and audit log | FR-025, FR-026, FR-027, FR-028 |
| P4-T10 | Phase 4 | Build HITL review interface UI | FR-023, FR-024, FR-025 |
| P5-T01 | Phase 5 | Implement email notification task | FR-029, FR-030 |
| P5-T02 | Phase 5 | Implement Excel export | FR-031, FR-033 |
| P5-T03 | Phase 5 | Implement CSV export | FR-032, FR-033 |
| P5-T04 | Phase 5 | Build results grid UI | FR-034 |
| P5-T05 | Phase 5 | Build export controls UI | FR-031, FR-032 |
| P5-T06 | Phase 5 | Frontend navigation and application shell integration | All FR |
| P5-T07 | Phase 5 | Error handling and loading states | All FR |
| P5-T08 | Phase 5 | End-to-end acceptance testing | Spec §6 AC-001–AC-007 |

---

## 10. Document Control

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | February 2026 | Product Team | Initial development plan |
