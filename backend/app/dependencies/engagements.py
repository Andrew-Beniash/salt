import uuid

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.engagement import Engagement
from app.models.user import User
from app.repositories.engagements import get_engagement, is_user_in_engagement

async def get_engagement_or_404(
    engagement_id: uuid.UUID = Path(..., alias="id"),
    db: AsyncSession = Depends(get_db)
) -> Engagement:
    engagement = await get_engagement(db, engagement_id)
    if not engagement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Engagement not found"
        )
    return engagement

async def get_engagement_or_403(
    engagement: Engagement = Depends(get_engagement_or_404),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Engagement:
    if getattr(user, "is_superuser", False):
        return engagement
        
    is_member = await is_user_in_engagement(db, engagement.id, user.id)
    if not is_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not assigned to this engagement"
        )
    return engagement

async def get_engagement_creator_or_admin(
    engagement: Engagement = Depends(get_engagement_or_404),
    user: User = Depends(get_current_user),
) -> Engagement:
    if getattr(user, "is_superuser", False):
        return engagement
        
    if engagement.created_by != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the engagement creator or an admin can modify membership"
        )
    return engagement
