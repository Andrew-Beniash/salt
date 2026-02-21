from fastapi import APIRouter, Depends
from app.models.user import User
from app.dependencies.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/me", summary="Get current user profile")
async def get_me(user: User = Depends(get_current_user)) -> dict:
    """Return the profile of the currently authenticated user."""
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }
