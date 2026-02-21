"""SQLAlchemy ORM models.

All models import ``Base`` from here and register themselves on it:

    from app.models import Base

    class Engagement(Base):
        __tablename__ = "engagements"
        ...

Alembic's env.py also imports ``Base.metadata`` so that autogenerate
can detect schema changes.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model in this project."""
