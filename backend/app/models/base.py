from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base.

    Import *this* class in every ORM model file::

        from app.models.base import Base
    """
