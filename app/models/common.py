from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class AttachmentRef(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "attachment_id": "64f9b8c1f1e4a9fd1a2b3c4d",
                "label": "Runbook PDF",
                "tags": ["runbook", "pdf"],
                "added_by": "64f9b8c1f1e4a9fd1a2b3c4d",
                "added_at": "2025-01-01T10:00:00Z",
            }
        },
    )

    attachment_id: str = Field(alias="attachment_id")
    label: Optional[str] = None
    tags: List[str] = []
    added_by: Optional[str] = None
    added_at: Optional[datetime] = None
