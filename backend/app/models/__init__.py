"""SQLAlchemy ORM models.

Import ``Base`` and any model class from here::

    from app.models import Base, User, Engagement

Alembic's env.py also imports ``Base.metadata`` so that autogenerate
can detect schema changes.

All submodule imports below register every model class on ``Base.metadata``
so that Alembic sees every table when ``target_metadata`` is set.
"""

from app.models.base import Base

# Register all models with Base.metadata (import order respects FK deps)
from app.models.user import User
from app.models.engagement import Engagement, EngagementMember, OneDriveFolder
from app.models.document import Document
from app.models.extraction import Extraction
from app.models.review_log import ReviewLog
from app.models.routing_log import RoutingLog

__all__ = [
    "Base",
    "User",
    "Engagement",
    "EngagementMember",
    "OneDriveFolder",
    "Document",
    "Extraction",
    "ReviewLog",
    "RoutingLog",
]
