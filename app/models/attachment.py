from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.models.common import AttachmentRef


class AttachmentLink(BaseModel):
    release_id: Optional[str] = None
    application_id: Optional[str] = None
    product_id: Optional[str] = None
    runbook_id: Optional[str] = None
    runbook_task_name: Optional[str] = None
    gate_name: Optional[str] = None
    milestone_key: Optional[str] = None
    ctask_id: Optional[str] = None


class Attachment(BaseModel):
    model_config = ConfigDict(populate_by_name=True, json_encoders={ObjectId: str})

    id: Optional[str] = Field(default=None, alias="_id")
    file_name: str
    file_type: str
    file_size: int
    file_url: str
    sha256: str
    tags: List[str] = []
    uploaded_by: Optional[str] = None
    uploaded_at: datetime
    links: List[AttachmentLink] = []
