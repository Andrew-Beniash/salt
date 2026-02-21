"""Data-access repositories.

Repositories wrap SQLAlchemy async sessions and expose typed query
methods.  They are the only layer that touches the ORM directly; services
call repositories instead of running queries inline.
"""
