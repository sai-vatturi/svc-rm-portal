from __future__ import annotations

from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class ApplicationProduct(BaseModel):
    product_id: str
    product_name: str
    product_owner_ids: List[str] = []
    product_pe_ids: List[str] = []
    product_jira_board_ids: List[str] = []
    product_squad_ids: List[str] = []


class Application(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "application_id": "APP1",
                "application_name": "Demo App",
                "technologies": ["python", "fastapi"],
                "description": "A sample application",
                "products": [
                    {"product_id": "PROD1", "product_name": "Core Service"}
                ],
            }
        },
    )

    id: Optional[str] = Field(default=None, alias="_id")
    application_id: str
    application_name: str
    technologies: List[str] = []
    description: Optional[str] = None
    products: List[ApplicationProduct] = []


class Squad(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "squad_id": "SQUAD1",
                "squad_name": "Platform Squad",
                "squad_jira_board_ids": [],
                "member_ids": []
            }
        },
    )

    id: Optional[str] = Field(default=None, alias="_id")
    squad_id: str
    squad_name: str
    squad_jira_board_ids: List[str] = []
    member_ids: List[str] = []


class JiraBoard(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={ObjectId: str},
        json_schema_extra={
            "example": {
                "board_id": "BOARD1",
                "board_name": "Demo Board",
                "board_link": "https://jira.example.com/board/1",
                "board_type": "scrum"
            }
        },
    )

    id: Optional[str] = Field(default=None, alias="_id")
    board_id: str
    board_name: str
    board_link: Optional[str] = None
    board_type: Optional[str] = None
