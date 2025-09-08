from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, require_permissions
from app.db.client import get_db
from app.models.catalog import Application, JiraBoard, Squad
from app.utils.time import utcnow

router = APIRouter()


def db():
    return get_db()


@router.post("/applications", response_model=Application, summary="Create application")
async def create_application(payload: Application, principal=Depends(require_permissions("can_manage_roles"))):
    dbase = get_db()
    exists = await dbase.applications.find_one({"application_id": payload.application_id})
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application_id exists")
    data = payload.model_dump(by_alias=True)
    res = await dbase.applications.insert_one(data)
    data["_id"] = str(res.inserted_id)
    return Application.model_validate(data)


@router.get("/applications", response_model=list[Application], summary="List applications")
async def list_applications():
    dbase = get_db()
    items: list[Application] = []
    async for doc in dbase.applications.find().sort("application_id"):
        doc["_id"] = str(doc.get("_id"))
        items.append(Application.model_validate(doc))
    return items


@router.post("/squads", response_model=Squad, summary="Create squad")
async def create_squad(payload: Squad, principal=Depends(require_permissions("can_manage_roles"))):
    dbase = get_db()
    exists = await dbase.squads.find_one({"squad_id": payload.squad_id})
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="squad_id exists")
    data = payload.model_dump(by_alias=True)
    res = await dbase.squads.insert_one(data)
    data["_id"] = str(res.inserted_id)
    return Squad.model_validate(data)


@router.get("/squads", response_model=list[Squad], summary="List squads")
async def list_squads():
    dbase = get_db()
    items: list[Squad] = []
    async for doc in dbase.squads.find().sort("squad_id"):
        doc["_id"] = str(doc.get("_id"))
        items.append(Squad.model_validate(doc))
    return items


@router.post("/jiraboards", response_model=JiraBoard, summary="Create JIRA board")
async def create_board(payload: JiraBoard, principal=Depends(require_permissions("can_manage_roles"))):
    dbase = get_db()
    exists = await dbase.jiraboards.find_one({"board_id": payload.board_id})
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="board_id exists")
    data = payload.model_dump(by_alias=True)
    res = await dbase.jiraboards.insert_one(data)
    data["_id"] = str(res.inserted_id)
    return JiraBoard.model_validate(data)


@router.get("/jiraboards", response_model=list[JiraBoard], summary="List JIRA boards")
async def list_boards():
    dbase = get_db()
    items: list[JiraBoard] = []
    async for doc in dbase.jiraboards.find().sort("board_id"):
        doc["_id"] = str(doc.get("_id"))
        items.append(JiraBoard.model_validate(doc))
    return items
