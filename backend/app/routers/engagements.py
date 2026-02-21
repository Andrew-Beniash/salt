import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.engagements import get_engagement_or_403, get_engagement_creator_or_admin
from app.models.engagement import Engagement
from app.models.user import User
from app.repositories import engagements as repo
from app.repositories import users as users_repo
from app.schemas.engagement import (
    EngagementCreate, EngagementOut, EngagementUpdate,
    EngagementMemberCreate, EngagementMemberOut,
    OneDriveFolderCreate, OneDriveFolderOut,
    SchemaField, SchemaIn, SchemaOut,
)

router = APIRouter(prefix="/engagements", tags=["engagements"])

@router.post("", response_model=EngagementOut, status_code=status.HTTP_201_CREATED)
async def create_engagement(
    engagement_in: EngagementCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new engagement and assign the creator as the lead."""
    return await repo.create_engagement(
        db,
        client_name=engagement_in.client_name,
        client_id=engagement_in.client_id,
        tax_year=engagement_in.tax_year,
        project_name=engagement_in.project_name,
        created_by=user.id
    )

@router.get("", response_model=List[EngagementOut])
async def list_engagements(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all engagements the current user is assigned to."""
    is_superuser = getattr(user, "is_superuser", False)
    return await repo.list_engagements_for_user(db, user.id, is_superuser=is_superuser)

@router.get("/{id}", response_model=EngagementOut)
async def get_engagement(
    engagement: Engagement = Depends(get_engagement_or_403)
):
    """Get a specific engagement if assigned."""
    return engagement

@router.patch("/{id}", response_model=EngagementOut)
async def update_engagement(
    engagement_in: EngagementUpdate,
    engagement: Engagement = Depends(get_engagement_or_403),
    db: AsyncSession = Depends(get_db)
):
    """Update an engagement. Only allowed if status is draft."""
    if engagement.status in ["processing", "complete"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update an engagement in {engagement.status} status."
        )

    update_data = engagement_in.model_dump(exclude_unset=True)
    if not update_data:
        return engagement

    return await repo.update_engagement(db, engagement, update_data)

@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_engagement(
    engagement: Engagement = Depends(get_engagement_or_403),
    db: AsyncSession = Depends(get_db)
):
    """Delete an engagement. Only allowed if status is draft."""
    if engagement.status in ["processing", "complete"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete an engagement in {engagement.status} status."
        )

    await repo.delete_engagement(db, engagement)

@router.post("/{id}/members", response_model=List[EngagementMemberOut])
async def add_engagement_member(
    member_in: EngagementMemberCreate,
    engagement: Engagement = Depends(get_engagement_creator_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Add a team member to an engagement (lookup by email). Creator/Admin only."""
    user = await users_repo.get_user_by_email(db, member_in.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {member_in.email} not found"
        )
    
    is_already_member = await repo.is_user_in_engagement(db, engagement.id, user.id)
    if not is_already_member:
        await repo.add_member(db, engagement.id, user.id, member_in.role)
        
    return await repo.get_members(db, engagement.id)

@router.delete("/{id}/members/{user_id}", response_model=List[EngagementMemberOut])
async def remove_engagement_member(
    user_id: uuid.UUID,
    engagement: Engagement = Depends(get_engagement_creator_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Remove a team member from an engagement. Creator/Admin only."""
    members = await repo.get_members(db, engagement.id)
    if len(members) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last member of an engagement."
        )
        
    # Check if the user is in the engagement
    member_to_remove = next((m for m in members if m.user_id == user_id), None)
    if member_to_remove:
        await repo.remove_member(db, engagement.id, user_id)
        
    return await repo.get_members(db, engagement.id)

@router.post("/{id}/folders", response_model=List[OneDriveFolderOut])
async def add_engagement_folder(
    folder_in: OneDriveFolderCreate,
    engagement: Engagement = Depends(get_engagement_creator_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Register an OneDrive folder against an engagement. Creator/Admin only."""
    if engagement.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot add folder to an engagement in {engagement.status} status."
        )

    await repo.add_folder(
        db, engagement.id, folder_in.folder_path, folder_in.display_name, folder_in.microsoft_user
    )
    return await repo.get_folders(db, engagement.id)

@router.delete("/{id}/folders/{folder_id}", response_model=List[OneDriveFolderOut])
async def remove_engagement_folder(
    folder_id: uuid.UUID,
    engagement: Engagement = Depends(get_engagement_creator_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """Remove a registered folder from an engagement. Creator/Admin only."""
    if engagement.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot remove folder from an engagement in {engagement.status} status."
        )

    folders = await repo.get_folders(db, engagement.id)
    if len(folders) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last folder from an engagement."
        )
        
    folder_to_remove = next((f for f in folders if f.id == folder_id), None)
    if folder_to_remove:
        await repo.remove_folder(db, engagement.id, folder_id)

    return await repo.get_folders(db, engagement.id)


# ── Output schema (FR-014) ────────────────────────────────────────────────────

# Statuses that lock schema changes
_SCHEMA_LOCKED_STATUSES = {"processing", "complete"}


@router.get("/{id}/schema", response_model=SchemaOut, summary="Get output schema")
async def get_output_schema(
    engagement: Engagement = Depends(get_engagement_or_403),
) -> SchemaOut:
    """Return the current output schema for the engagement.

    Returns an empty ``fields`` list when no schema has been saved yet.
    """
    raw: list[dict] = engagement.output_schema if isinstance(engagement.output_schema, list) else []
    return SchemaOut(fields=[SchemaField(**f) for f in raw])


@router.post("/{id}/schema", response_model=SchemaOut, summary="Save output schema")
async def save_output_schema(
    schema_in: SchemaIn,
    engagement: Engagement = Depends(get_engagement_or_403),
    db: AsyncSession = Depends(get_db),
) -> SchemaOut:
    """Replace the output schema for an engagement.

    - Field ``name`` must be unique within the schema and contain only
      letters, digits, and underscores (starting with a letter or underscore).
    - Returns HTTP 409 when the engagement is in ``processing`` or ``complete``
      status; schema changes are locked at that point.
    """
    if engagement.status in _SCHEMA_LOCKED_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Output schema cannot be modified once the engagement is in "
                f"'{engagement.status}' status."
            ),
        )

    fields_data = [f.model_dump() for f in schema_in.fields]
    updated = await repo.save_schema(db, engagement, fields_data)
    return SchemaOut(fields=[SchemaField(**f) for f in updated.output_schema])

