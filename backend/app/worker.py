import os

from celery import Celery

_broker = os.getenv("REDIS_URL", "redis://redis:6379/0")
_backend = os.getenv("REDIS_URL", "redis://redis:6379/0")

app = Celery("salt", broker=_broker, backend=_backend)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Acknowledge tasks only after completion so crashes auto-requeue
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "tasks.ingestion.*": {"queue": "ingestion"},
        "tasks.extraction.*": {"queue": "extraction"},
        "tasks.routing.*": {"queue": "routing"},
        "tasks.notification.*": {"queue": "notification"},
    },
)
