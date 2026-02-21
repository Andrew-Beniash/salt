from app.celery_app import app
import time
import logging

logger = logging.getLogger(__name__)

@app.task
def sample_notification_task(doc_id: str, message: str):
    logger.info(f"Sending notification for document {doc_id}: {message}")
    time.sleep(1)
    logger.info(f"Sent notification for document {doc_id}")
    return {"status": "success", "queue": "notification", "doc_id": doc_id}
