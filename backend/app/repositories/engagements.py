from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.engagement import Engagement, EngagementMember, OneDriveFolder

async def create_engagement(
    db: AsyncSession,
    *,
    client_name: str,
    client_id: str,
    tax_year: int,
    project_name: str,
    created_by: uuid.UUID
) -> Engagement:
    engagement = Engagement(
        client_name=client_name,
        client_id=client_id,
        tax_year=tax_year,
        project_name=project_name,
        created_by=created_by,
        status="draft"
    )
    db.add(engagement)
    await db.flush()
    
    # Automatically add the creator as lead
    member = EngagementMember(
        engagement_id=engagement.id,
        user_id=created_by,
        role="lead"
    )
    db.add(member)
    await db.commit()
    await db.refresh(engagement)
    
    return engagement

async def list_engagements_for_user(
    db: AsyncSession, user_id: uuid.UUID, is_superuser: bool = False
) -> list[Engagement]:
    if is_superuser:
        query = select(Engagement).order_by(Engagement.created_at.desc())
    else:
        query = (
            select(Engagement)
            .join(EngagementMember, EngagementMember.engagement_id == Engagement.id)
            .where(EngagementMember.user_id == user_id)
            .order_by(Engagement.created_at.desc())
        )
    
    result = await db.execute(query)
    return list(result.scalars().all())

async def get_engagement(
    db: AsyncSession, engagement_id: uuid.UUID
) -> Engagement | None:
    result = await db.execute(select(Engagement).where(Engagement.id == engagement_id))
    return result.scalar_one_or_none()

async def is_user_in_engagement(
    db: AsyncSession, engagement_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    query = select(EngagementMember).where(
        EngagementMember.engagement_id == engagement_id,
        EngagementMember.user_id == user_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None

async def update_engagement(
    db: AsyncSession, engagement: Engagement, update_data: dict
) -> Engagement:
    for key, value in update_data.items():
        setattr(engagement, key, value)
    db.add(engagement)
    await db.commit()
    await db.refresh(engagement)
    return engagement

async def delete_engagement(
    db: AsyncSession, engagement: Engagement
) -> None:
    await db.delete(engagement)
    await db.commit()

async def get_members(db: AsyncSession, engagement_id: uuid.UUID) -> list[EngagementMember]:
    result = await db.execute(select(EngagementMember).where(EngagementMember.engagement_id == engagement_id))
    return list(result.scalars().all())

async def add_member(db: AsyncSession, engagement_id: uuid.UUID, user_id: uuid.UUID, role: str) -> EngagementMember:
    member = EngagementMember(engagement_id=engagement_id, user_id=user_id, role=role)
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member

async def remove_member(db: AsyncSession, engagement_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(select(EngagementMember).where(
        EngagementMember.engagement_id == engagement_id,
        EngagementMember.user_id == user_id
    ))
    member = result.scalar_one_or_none()
    if member:
        await db.delete(member)
        await db.commit()

async def get_folders(db: AsyncSession, engagement_id: uuid.UUID) -> list[OneDriveFolder]:
    result = await db.execute(select(OneDriveFolder).where(OneDriveFolder.engagement_id == engagement_id))
    return list(result.scalars().all())

async def add_folder(
    db: AsyncSession, engagement_id: uuid.UUID, folder_path: str, display_name: str | None, microsoft_user: str | None
) -> OneDriveFolder:
    folder = OneDriveFolder(
        engagement_id=engagement_id,
        folder_path=folder_path,
        display_name=display_name,
        microsoft_user=microsoft_user
    )
    db.add(folder)
    await db.commit()
    await db.refresh(folder)
    return folder

async def remove_folder(db: AsyncSession, engagement_id: uuid.UUID, folder_id: uuid.UUID) -> None:
    result = await db.execute(select(OneDriveFolder).where(
        OneDriveFolder.engagement_id == engagement_id,
        OneDriveFolder.id == folder_id
    ))
    folder = result.scalar_one_or_none()
    if folder:
        await db.delete(folder)
        await db.commit()

async def get_engagement_progress(db: AsyncSession, engagement_id: uuid.UUID) -> dict:
    from app.models.document import Document
    from sqlalchemy import func
    
    query = select(Document.status, func.count(Document.id)).where(
        Document.engagement_id == engagement_id
    ).group_by(Document.status)
    
    result = await db.execute(query)
    counts = dict(result.all())
    
    # Base fields that match the exact status strings
    progress = {
        "discovered": counts.get("discovered", 0),
        "validated": counts.get("validated", 0),
        "rejected": counts.get("rejected", 0),
        "downloaded": counts.get("downloaded", 0),
        "queued": counts.get("queued", 0),
        "extracting": counts.get("extracting", 0),
        "auto_approved": counts.get("auto_approved", 0),
        "pending_review": counts.get("pending_review", 0),
        "confirmed": counts.get("confirmed", 0),
        "corrected": counts.get("corrected", 0),
        "extraction_failed": counts.get("extraction_failed", 0),
        "download_failed": counts.get("download_failed", 0),
    }
    
    total = sum(progress.values())
    
    terminal_statuses = {
        "auto_approved", "confirmed", "corrected", 
        "rejected", "extraction_failed", "download_failed"
    }
    
    terminal_count = sum(progress[s] for s in terminal_statuses)
    
    progress["total"] = total
    progress["percent_complete"] = (terminal_count / total * 100.0) if total > 0 else 0.0
    
    return progress

async def get_rejected_documents(db: AsyncSession, engagement_id: uuid.UUID) -> list:
    from app.models.document import Document
    result = await db.execute(
        select(Document)
        .where(
            Document.engagement_id == engagement_id,
            Document.status == "rejected"
        )
        .order_by(Document.discovered_at.desc())
    )
    return list(result.scalars().all())



async def save_schema(
    db: AsyncSession,
    engagement: Engagement,
    fields: list[dict],
) -> Engagement:
    """Persist the output schema (list of field dicts) on the engagement row."""
    engagement.output_schema = fields
    db.add(engagement)
    await db.commit()
    await db.refresh(engagement)
    return engagement


async def activate_engagement(
    db: AsyncSession,
    engagement: Engagement,
) -> Engagement:
    """Transition an engagement from draft → processing and stamp activated_at."""
    now = datetime.now(timezone.utc)
    engagement.status = "processing"
    engagement.activated_at = now
    engagement.updated_at = now
    db.add(engagement)
    await db.commit()
    await db.refresh(engagement)
    return engagement
