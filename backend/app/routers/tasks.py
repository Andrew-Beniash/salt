from fastapi import APIRouter
from app.tasks.ingestion import sample_ingestion_task
from app.tasks.extraction import sample_extraction_task
from app.tasks.routing import sample_routing_task
from app.tasks.notification import sample_notification_task

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/test-dispatch")
async def dispatch_test_tasks(doc_id: str):
    """Dispatch a sample task to each of the 4 Celery queues."""
    # dispatch asynchronous tasks
    t1 = sample_ingestion_task.delay(doc_id)
    t2 = sample_extraction_task.delay(doc_id)
    t3 = sample_routing_task.delay(doc_id)
    t4 = sample_notification_task.delay(doc_id, message="Test notification")

    return {
        "status": "Tasks dispatched",
        "doc_id": doc_id,
        "task_ids": {
            "ingestion": t1.id,
            "extraction": t2.id,
            "routing": t3.id,
            "notification": t4.id
        }
    }
