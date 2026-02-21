from app.celery_app import app
import time
import logging

logger = logging.getLogger(__name__)

@app.task
def sample_ingestion_task(doc_id: str):
    logger.info(f"Starting ingestion for document {doc_id}")
    time.sleep(2)
    logger.info(f"Finished ingestion for document {doc_id}")
    return {"status": "success", "queue": "ingestion", "doc_id": doc_id}
