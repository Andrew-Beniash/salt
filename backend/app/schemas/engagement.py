import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

class EngagementCreate(BaseModel):
    client_name: str = Field(..., max_length=255)
    client_id: str = Field(..., max_length=100)
    tax_year: int
    project_name: str = Field(..., max_length=255)

class EngagementUpdate(BaseModel):
    client_name: str | None = Field(None, max_length=255)
    client_id: str | None = Field(None, max_length=100)
    tax_year: int | None = None
    project_name: str | None = Field(None, max_length=255)
    status: str | None = Field(None, max_length=50)
    confidence_threshold: int | None = Field(None, ge=0, le=100)
    output_schema: dict | list | None = None

class EngagementOut(BaseModel):
    id: uuid.UUID
    client_name: str
    client_id: str
    tax_year: int
    project_name: str
    status: str
    confidence_threshold: int
    output_schema: dict | list | None
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ActivationOut(BaseModel):
    """Response body for POST /engagements/{id}/activate."""

    status: str

class EngagementMemberCreate(BaseModel):
    email: str = Field(..., max_length=255)
    role: str = Field(default="reviewer", max_length=50)

class EngagementMemberOut(BaseModel):
    engagement_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)

class OneDriveFolderCreate(BaseModel):
    folder_path: str = Field(..., max_length=1000)
    display_name: str | None = Field(None, max_length=255)
    microsoft_user: str | None = Field(None, max_length=255)

class OneDriveFolderOut(BaseModel):
    id: uuid.UUID
    engagement_id: uuid.UUID
    folder_path: str
    display_name: str | None
    microsoft_user: str | None
    registered_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Output schema builder (FR-014) ────────────────────────────────────────────

class FieldType(str, Enum):
    text = "text"
    currency = "currency"
    date = "date"
    number = "number"


class SchemaField(BaseModel):
    """A single field in an engagement's output schema."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$",
        description=(
            "Machine key used in extraction output. "
            "Only letters, digits, and underscores; must start with a letter or underscore."
        ),
    )
    label: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable display name shown in the review UI.",
    )
    type: FieldType = Field(..., description="Data type hint for the extraction model.")


class SchemaIn(BaseModel):
    """Request body for POST /engagements/{id}/schema."""

    fields: list[SchemaField] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _unique_field_names(self) -> "SchemaIn":
        names = [f.name for f in self.fields]
        duplicates = sorted({n for n in names if names.count(n) > 1})
        if duplicates:
            raise ValueError(f"Duplicate field names: {', '.join(duplicates)}")
        return self


class SchemaOut(BaseModel):
    """Response body for GET and POST /engagements/{id}/schema."""

    fields: list[SchemaField]

class EngagementProgress(BaseModel):
    discovered: int = 0
    validated: int = 0
    rejected: int = 0
    downloaded: int = 0
    queued: int = 0
    extracting: int = 0
    auto_approved: int = 0
    pending_review: int = 0
    confirmed: int = 0
    corrected: int = 0
    extraction_failed: int = 0
    download_failed: int = 0
    
    total: int = 0
    percent_complete: float = 0.0

