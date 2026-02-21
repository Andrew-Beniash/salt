# TaxAutomation Platform — Functional Specification

**Version 1.0 | February 2026**

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Functional Requirements](#2-functional-requirements)
   - 2.1 [Engagement Management](#21-engagement-management)
   - 2.2 [Document Ingestion](#22-document-ingestion)
   - 2.3 [AI Extraction Engine](#23-ai-extraction-engine)
   - 2.4 [Human-in-the-Loop Review](#24-human-in-the-loop-review)
   - 2.5 [Notifications and Export](#25-notifications-and-export)
3. [Non-Functional Requirements](#3-non-functional-requirements)
   - 3.1 [Performance](#31-performance)
   - 3.2 [Reliability](#32-reliability)
   - 3.3 [Security](#33-security)
   - 3.4 [Accuracy](#34-accuracy)
4. [Technology Stack](#4-technology-stack)
5. [Constraints and Assumptions](#5-constraints-and-assumptions)
6. [Acceptance Criteria](#6-acceptance-criteria)
7. [Roles and Responsibilities](#7-roles-and-responsibilities)
8. [Key Decision Points](#8-key-decision-points)
9. [Document Control](#9-document-control)

---

## 1. Introduction

### 1.1 Purpose

This document is the formal functional specification for the TaxAutomation Platform initial prototype. It defines what the system must do, the constraints it must operate within, and the criteria by which the prototype is considered complete. It serves as the authoritative reference for all development, testing, and stakeholder alignment activities.

### 1.2 Background

Tax compliance engagements — particularly Sales and Use Tax (SUT) recovery, audit defense, and exemption certificate validation — require processing tens of thousands of client documents per engagement. These processes are currently executed manually, resulting in engagement timelines of three to four months and significant labour cost. The TaxAutomation Platform addresses this by applying AI-powered document extraction, confidence-based routing, and structured output generation to compress engagement timelines to as little as two weeks while maintaining professional-grade accuracy and full audit compliance.

### 1.3 Scope

The initial prototype covers the following functional areas:

- Engagement creation and team management
- OneDrive-integrated document ingestion (up to 50,000 documents per engagement)
- AI-powered configurable field extraction from tax documents
- Confidence-based human-in-the-loop review workflows
- Structured export of results to Excel and CSV formats
- Email notification upon engagement processing completion

Enterprise features including multi-tenant architecture, advanced role-based access control, and production-grade observability are out of scope for the prototype and deferred to subsequent phases.

### 1.4 Definitions

| Term | Definition |
|---|---|
| **Engagement** | A discrete client project defined by client name, client ID, tax year, and project name, within which all document processing occurs. |
| **Confidence Score** | A numerical value (0–100%) assigned by the AI extraction engine to each processed document, reflecting the system's certainty in the accuracy of the extracted datapoints. |
| **HITL Review** | Human-in-the-loop review — a workflow step in which a tax professional manually validates, corrects, or rejects AI-extracted results for documents below the confidence threshold. |
| **Output Schema** | The user-defined set of datapoints to be extracted per engagement, such as document name, sales tax amount, date, jurisdiction, and seller. |
| **OCR** | Optical Character Recognition — the process of extracting machine-readable text from document images or PDFs. |
| **Extraction Pipeline** | The sequential processing chain that takes a raw document from ingestion through OCR, AI extraction, confidence scoring, and routing. |
| **Auto-Approved** | A document whose confidence score meets or exceeds the engagement threshold and is therefore approved for export without human review. |

---

## 2. Functional Requirements

### 2.1 Engagement Management

| ID | Requirement | Priority |
|---|---|---|
| **FR-001** | The system shall allow users to create a new engagement by providing: client name, client ID, tax year, and project name. | High |
| **FR-002** | The system shall allow users to assign one or more team members to each engagement. | High |
| **FR-003** | The system shall restrict engagement access to assigned team members and system administrators. Users not assigned to an engagement shall receive no access to its data. | High |
| **FR-004** | The system shall display a list of all engagements accessible to the authenticated user, including status indicators for each engagement. | High |
| **FR-005** | The system shall allow users to update engagement metadata (client name, project name, tax year) after creation, provided processing has not yet been activated. | Medium |
| **FR-006** | The system shall allow users to remove team members from an engagement. | Medium |

### 2.2 Document Ingestion

| ID | Requirement | Priority |
|---|---|---|
| **FR-007** | The system shall allow users to define one or more OneDrive folders as document sources for each engagement using Microsoft Graph API with OAuth 2.0 authentication. | High |
| **FR-008** | The system shall support document ingestion in PDF, TIFF, JPEG, and PNG formats. | High |
| **FR-009** | The system shall be capable of processing up to 50,000 documents per engagement. Documents beyond this limit shall be logged and excluded with a clear reason. | High |
| **FR-010** | The system shall handle varying document layouts, structures, and quality levels within the same engagement without requiring per-template configuration. | High |
| **FR-011** | The system shall validate each document at ingestion time and reject unsupported file types with a logged rejection reason. | High |
| **FR-012** | The system shall track ingestion status at the document level and provide real-time progress visibility to team members, showing counts for: discovered, downloading, queued, processing, completed, failed, and rejected. | Medium |
| **FR-013** | The system shall allow processing to be activated by an authorised team member only after at least one folder and one output schema field have been defined. | High |

### 2.3 AI Extraction Engine

| ID | Requirement | Priority |
|---|---|---|
| **FR-014** | The system shall allow users to define a configurable output schema per engagement, specifying the datapoints to be extracted. Examples include: document link, document name, sales tax, date, jurisdiction, seller, buyer, and invoice number. | High |
| **FR-015** | The system shall extract the user-defined datapoints from each document using a three-tier processing pipeline: native PDF extraction (pdfplumber), structured OCR (Azure Document Intelligence), and LLM-based extraction (OpenAI API). | High |
| **FR-016** | The system shall route each document through extraction tiers in order of cost and speed, escalating to the next tier only when the confidence score from the current tier falls below that tier's threshold. | High |
| **FR-017** | The system shall assign a confidence score (0–100%) to each processed document, reflecting the extraction engine's certainty across all extracted fields. | High |
| **FR-018** | The system shall correctly extract data from documents with varying formats, layouts, and quality without requiring per-template configuration. | High |
| **FR-019** | The system shall store the full extraction result including field values, confidence score, extraction method used, and raw OCR text for audit purposes. | High |
| **FR-020** | The system shall support pre-processing of scanned documents and images using OpenCV to improve OCR accuracy (deskew, denoise, binarise) before passing to the extraction engine. | Medium |

### 2.4 Human-in-the-Loop Review

| ID | Requirement | Priority |
|---|---|---|
| **FR-021** | The system shall automatically flag documents with confidence scores below a configurable threshold for human review. The default threshold is 85%. | High |
| **FR-022** | The system shall allow the confidence threshold to be adjusted per engagement by an authorised user, within the range 0–100%. | Medium |
| **FR-023** | The system shall present flagged documents to assigned team members in a dedicated review interface, ordered by confidence score ascending (lowest confidence first). | High |
| **FR-024** | The review interface shall display the source document rendered inline alongside the AI-extracted field values for side-by-side comparison. | High |
| **FR-025** | Reviewers shall be able to perform one of three actions on each flagged document: confirm (accept AI values as-is), correct (override one or more field values), or reject (exclude document from output). | High |
| **FR-026** | The system shall record the identity of the reviewer and the timestamp of each review action against the document record. | High |
| **FR-027** | The system shall maintain an immutable audit log of all review actions. No review log entry may be modified or deleted after creation. | High |
| **FR-028** | Corrected field values submitted by reviewers shall be saved to the extraction record and used in the final export in place of the original AI-extracted values. | High |

### 2.5 Notifications and Export

| ID | Requirement | Priority |
|---|---|---|
| **FR-029** | The system shall send an email notification to all engagement team members when all documents in the engagement have reached a terminal processing status (auto-approved, confirmed, corrected, rejected, or failed). | High |
| **FR-030** | The completion email shall include: engagement name, client name, tax year, total document count, auto-approved count, reviewed count, rejected count, and a direct link to the results screen. | Medium |
| **FR-031** | The system shall allow users to export extraction results in Microsoft Excel (.xlsx) format. | High |
| **FR-032** | The system shall allow users to export extraction results in CSV format. | High |
| **FR-033** | Exported files shall include one row per document with columns for: all configured output schema fields, confidence score, review status, reviewer identity (where applicable), review timestamp (where applicable), extraction method, and source document link. | High |
| **FR-034** | The system shall display all extraction results in a paginated, sortable, filterable data grid within the application. | High |

---

## 3. Non-Functional Requirements

### 3.1 Performance

- The system shall process a minimum of 100 documents per minute under standard operating conditions.
- The system shall complete processing of 50,000 documents within a single working day.
- The review interface shall load the flagged document queue within three seconds.
- The results data grid shall render up to 50,000 rows without perceptible degradation in scroll performance, using virtual rendering.
- Export file generation for up to 50,000 rows shall complete within 60 seconds.

### 3.2 Reliability

- The system shall achieve 99.9% uptime during active engagement processing windows.
- Failed document download attempts shall be automatically retried up to three times with exponential backoff before being marked as failed.
- Failed extraction attempts shall be automatically retried up to three times before the document is marked as extraction-failed.
- The system shall preserve all processing state in the event of an unexpected interruption, enabling resumption from the last completed stage without data loss or reprocessing.
- Workers that crash mid-task shall have their in-progress tasks automatically requeued and retried.

### 3.3 Security

- All user authentication shall be enforced via JWT-based access tokens with appropriate expiry. Tokens shall be validated on every API request.
- OneDrive integration shall use OAuth 2.0 with Microsoft identity platform. No client Microsoft credentials shall be stored in the system — only MSAL-managed access and refresh tokens.
- Engagement data shall be logically isolated. Team members may only access engagements to which they are explicitly assigned.
- Microsoft refresh tokens shall be stored encrypted at rest using symmetric encryption. The encryption key shall be injected via environment variable.
- No API keys, credentials, or sensitive tokens shall be logged, included in error messages, or returned in API responses.

### 3.4 Accuracy

- The AI extraction engine shall achieve a field-level accuracy rate of 95% or above on clean, native digital PDF documents.
- The confidence scoring mechanism shall correctly identify low-confidence extractions, with a false-negative rate (confident but wrong) below 5%.
- The three-tier extraction cascade shall route approximately 40% of documents through pdfplumber, 45% through Azure Document Intelligence, and 15% through OpenAI, for a typical clean invoice engagement.

---

## 4. Technology Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python / FastAPI | 3.12 / 0.115+ |
| Task Queue | Celery | 5.4+ |
| Message Broker | Redis | 7.x |
| Database | PostgreSQL | 16.x |
| OCR Tier 1 | pdfplumber | Latest |
| OCR Tier 2 | Azure Document Intelligence | Latest SDK |
| OCR Tier 3 | OpenAI API (gpt-4o-mini) | Latest |
| Image Pre-processing | OpenCV + Pillow | Latest |
| Document Source | Microsoft Graph API | v1.0 |
| File Storage | Local filesystem (prototype) | — |
| Email | SendGrid | — |
| Export | openpyxl + csv | Latest |
| Frontend | React + TypeScript + shadcn/ui | 18.x / 5.x |
| Data Grid | TanStack Table | v8 |
| Authentication | Supabase Auth / JWT | Latest |
| Infrastructure | Docker Compose | v2 |

---

## 5. Constraints and Assumptions

### 5.1 Constraints

- The prototype is scoped to the functional areas defined in Section 2. Enterprise features are deferred.
- Document processing is limited to supported formats: PDF, TIFF, JPEG, and PNG. Other file types will be rejected at ingestion.
- AI extraction accuracy is subject to input document quality. Scanned documents with low resolution or heavy distortion may yield lower confidence scores and require human review.
- OneDrive integration requires users to authenticate with a valid Microsoft account that has read access to the specified folders.
- Azure Document Intelligence free tier is limited to 500 pages per month. Engagements exceeding this volume will consume paid API quota.
- OpenAI API access requires a funded account. No free tier is available for API usage.

### 5.2 Assumptions

- Users accessing the platform have been provisioned with valid Supabase credentials by a system administrator.
- Client documents stored in OneDrive are organised in folder structures accessible via Microsoft Graph API.
- The OpenAI API will remain available at the throughput levels required to process the estimated 15% of documents routed to the LLM tier.
- Email delivery will be handled via SendGrid. Sender email addresses will be verified in SendGrid before the application goes live.
- The prototype will be deployed on a single VM using Docker Compose. No container orchestration is required for the prototype phase.

---

## 6. Acceptance Criteria

The initial prototype is considered complete when all of the following criteria are satisfied:

| ID | Criterion | Verification Method |
|---|---|---|
| **AC-001** | A user can create an engagement, assign team members, connect OneDrive folders, and define an output schema successfully. | Functional walkthrough |
| **AC-002** | The system processes a batch of 500 mixed-format documents and extracts configured fields with 95%+ field-level accuracy. | Batch processing test |
| **AC-003** | Documents with confidence scores below the threshold are presented in the review queue. Reviewer confirm, correct, and reject actions are logged with user identity and timestamp. | Review workflow walkthrough |
| **AC-004** | An email notification is received by all team members upon engagement completion, containing the required summary statistics and results link. | Email delivery test |
| **AC-005** | Results are exported successfully in both Excel and CSV formats, containing all configured output fields, confidence scores, review status, and reviewer identity. | Export verification |
| **AC-006** | The three-tier OCR cascade correctly routes documents: native PDFs through pdfplumber, scanned documents through Azure DI, and complex or ambiguous documents through OpenAI. | Pipeline inspection test |
| **AC-007** | The immutable audit log records every review action. No modification or deletion of log entries is possible via any application interface or API call. | Audit log integrity test |

---

## 7. Roles and Responsibilities

| Role | Responsibilities |
|---|---|
| **Tax Professional** | Creates and configures engagements; defines output schema; manages team membership; activates document processing; conducts human review of flagged documents; triggers and downloads exports. |
| **System Administrator** | Provisions user accounts; manages system configuration; adjusts platform-level confidence thresholds; accesses all engagements. |
| **System (Automated)** | Ingests documents from OneDrive; executes the three-tier OCR and AI extraction pipeline; routes documents based on confidence scores; sends email notifications on completion; generates export files; maintains the immutable audit log. |

---

## 8. Key Decision Points

The process contains two primary decision points that determine downstream routing for every document:

| Decision Point | Condition Met | Condition Not Met |
|---|---|---|
| **Confidence Threshold — Step 4** | Score ≥ threshold → Document auto-approved and available for export immediately. | Score < threshold → Document routed to human review queue. |
| **Reviewer Action — Step 5** | Confirmed or Corrected → Reviewer identity and timestamp logged; document approved for export using confirmed or corrected values. | Rejected → Document marked as rejected; excluded from export; rejection logged in audit trail. |

---

## 9. Document Control

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0 | February 2026 | Product Team | Initial functional specification |
