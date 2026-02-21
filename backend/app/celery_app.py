from celery import Celery

from app.config import get_settings

_settings = get_settings()

app = Celery(
    "salt",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=[
        "app.tasks.ingestion",
        "app.tasks.extraction",
        "app.tasks.routing",
        "app.tasks.notification",
    ]
)

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
        "app.tasks.ingestion.*": {"queue": "ingestion"},
        "app.tasks.extraction.*": {"queue": "extraction"},
        "app.tasks.routing.*": {"queue": "routing"},
        "app.tasks.notification.*": {"queue": "notification"},
    },
)
