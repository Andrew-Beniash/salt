import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

class DocumentRejectedOut(BaseModel):
    id: uuid.UUID
    filename: str
    rejection_reason: str | None
    error_detail: str | None
    discovered_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
