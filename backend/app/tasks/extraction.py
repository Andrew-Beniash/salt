from app.celery_app import app
import time
import logging

logger = logging.getLogger(__name__)

@app.task(bind=True, name="app.tasks.extraction.extract_document")
def extract_document(self, document_id: str):
    logger.info(f"Starting extraction for document {document_id}")
    time.sleep(2)
    logger.info(f"Finished extraction for document {document_id}")
    return {"status": "success", "queue": "extraction", "document_id": document_id}
