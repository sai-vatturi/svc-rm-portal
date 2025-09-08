from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from app.models.common import AttachmentRef


class ReleaseFixedVersion(BaseModel):
    version_key: Optional[str] = None
    version_name: Optional[str] = None
    status: Optional[str] = None


class VersionBoard(BaseModel):
    jira_board_id: Optional[str] = None
    jira_board_link: Optional[str] = None
    fixed_version_link: Optional[str] = None


class ReleaseMilestone(BaseModel):
    milestone_key: str
    milestone_name: str
    environment: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    owner_id: Optional[str] = None
    attachment_refs: List[AttachmentRef] = []
    approval: Optional[dict] = None  # Simplified MVP; can model fully later


class ReleaseProductQualityGate(BaseModel):
    gate_name: str
    description: Optional[str] = None
    order: Optional[int] = None
    required: bool = True
    gate_status: Optional[str] = None
    owner_id: Optional[str] = None
    attachment_refs: List[AttachmentRef] = []
    milestones: List[ReleaseMilestone] = []


class ReleaseProduct(BaseModel):
    application_id: str
    product_id: str
    product_name: Optional[str] = None
    fixed_version: Optional[ReleaseFixedVersion] = None
    version_boards: List[VersionBoard] = []
    quality_gates: List[ReleaseProductQualityGate] = []
    attachment_refs: List[AttachmentRef] = []
    participating_squad_ids: List[str] = []


class ReleaseCTask(BaseModel):
    ctask_id: str
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[str] = None
    dependency_ctask_ids: List[str] = []
    attachment_refs: List[AttachmentRef] = []


class ReleaseChange(BaseModel):
    change_id: Optional[str] = None
    change_type: Optional[str] = None
    status: Optional[str] = None
    affected_ci: Optional[str] = None
    bp_signoff: Optional[bool] = None
    ctasks: List[ReleaseCTask] = []
    attachment_refs: List[AttachmentRef] = []


class ReleaseRunbookTask(BaseModel):
    task_name: str
    description: Optional[str] = None
    owner_id: Optional[str] = None
    environment: Optional[str] = None
    preconditions: List[str] = []
    commands: List[str] = []
    rollback_plan: Optional[str] = None
    validation_steps: List[str] = []
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    depends_on_task_names: List[str] = []
    status: Optional[str] = None
    attachment_refs: List[AttachmentRef] = []


class ReleaseRunbook(BaseModel):
    runbook_id: str
    runbook_name: str
    description: Optional[str] = None
    tasks: List[ReleaseRunbookTask] = []
    attachment_refs: List[AttachmentRef] = []
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None


class Release(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "release_id": "REL-0001",
                "release_name": "Initial",
                "release_date": "2025-09-09T10:00:00Z",
                "release_type": "MAJOR",
                "description": "Q3 major release",
                "scope_application_ids": [],
                "squad_ids": [],
                "products": [
                    {
                        "application_id": "64f9b8c1f1e4a9fd1a2b3c4d",
                        "product_id": "PROD1",
                        "quality_gates": [
                            {
                                "gate_name": "QA Signoff",
                                "required": True,
                                "milestones": [
                                    {
                                        "milestone_key": "QA-UAT",
                                        "milestone_name": "UAT Completed",
                                        "status": "NOT_STARTED",
                                    }
                                ],
                            }
                        ],
                    }
                ],
                "runbooks": [],
                "attachment_refs": [],
            }
        },
    )

    id: Optional[str] = Field(default=None, alias="_id")
    release_id: str
    release_name: str
    release_date: datetime
    release_type: Optional[str] = None
    description: Optional[str] = None
    scope_application_ids: List[str] = []
    squad_ids: List[str] = []
    products: List[ReleaseProduct] = []
    runbooks: List[ReleaseRunbook] = []
    chg: Optional[ReleaseChange] = None
    attachment_refs: List[AttachmentRef] = []
    created_by: Optional[str] = None
    created_at: datetime


# Request payloads
class ReleaseDescriptionUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"description": "Updated release description"}}
    )
    description: str


class UpdateQualityGate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "description": "Adjusted scope",
                "required": True,
                "gate_status": "IN_PROGRESS",
            }
        }
    )
    description: Optional[str] = None
    order: Optional[int] = None
    required: Optional[bool] = None
    gate_status: Optional[str] = None
    owner_id: Optional[str] = None


class UpdateMilestone(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"status": "DONE", "end_date": "2025-09-10T12:00:00Z"}
        }
    )
    milestone_name: Optional[str] = None
    environment: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None
    owner_id: Optional[str] = None


class ApproveMilestoneRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"example": {"comment": "Looks good"}}
    )
    comment: Optional[str] = None


class UpdateRunbookTask(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"status": "DONE", "scheduled_end": "2025-09-10T10:30:00Z"}
        }
    )
    description: Optional[str] = None
    owner_id: Optional[str] = None
    environment: Optional[str] = None
    scheduled_start: Optional[datetime] = None
    scheduled_end: Optional[datetime] = None
    status: Optional[str] = None
