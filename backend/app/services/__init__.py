"""Business-logic services.

Each service module encapsulates one bounded context (e.g. ingestion,
extraction, notification).  Services depend on repositories for data
access and may publish Celery tasks.
"""
