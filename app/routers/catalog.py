from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Query

from app.core.security import require_permissions
from app.db.client import get_db
from app.models.catalog import Application, JiraBoard, Squad
from app.repositories.catalog_repo import CatalogRepository

router = APIRouter()


def repo() -> CatalogRepository:
    return CatalogRepository(get_db())


PAGE_SIZE_MAX = 100


@router.post("/applications", response_model=Application, summary="Create application")
async def create_application(payload: Application, _=Depends(require_permissions("can_manage_roles"))):
    created = await repo().create_application(payload)
    if not created:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="application_id exists")
    return created


@router.get("/applications", response_model=list[Application], summary="List applications")
async def list_applications(skip: int = Query(0, ge=0), limit: int = Query(50, gt=0, le=PAGE_SIZE_MAX), q: str | None = None):
    dbase = get_db()
    crit = {}
    if q:
        crit = {"application_id": {"$regex": q, "$options": "i"}}
    items: list[Application] = []
    cursor = dbase.applications.find(crit).sort("application_id").skip(skip).limit(limit)
    async for doc in cursor:
        doc["_id"] = str(doc.get("_id"))
        items.append(Application.model_validate(doc))
    return items


@router.get("/applications/{id_or_key}", response_model=Application, summary="Get application by id or key")
async def get_application(id_or_key: str):
    a = await repo().get_application(id_or_key)
    if not a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return a


@router.patch("/applications/{app_id}", response_model=Application, summary="Update application (partial)")
async def update_application(app_id: str, patch: dict, _=Depends(require_permissions("can_manage_roles"))):
    updated = await repo().update_application(app_id, patch)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return updated


@router.delete("/applications/{app_id}", summary="Delete application")
async def delete_application(app_id: str, _=Depends(require_permissions("can_manage_roles"))):
    deleted = await repo().delete_application(app_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"deleted": deleted}


@router.post("/squads", response_model=Squad, summary="Create squad")
async def create_squad(payload: Squad, _=Depends(require_permissions("can_manage_roles"))):
    created = await repo().create_squad(payload)
    if not created:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="squad_id exists")
    return created


@router.get("/squads", response_model=list[Squad], summary="List squads")
async def list_squads(skip: int = Query(0, ge=0), limit: int = Query(50, gt=0, le=PAGE_SIZE_MAX), q: str | None = None):
    dbase = get_db()
    crit = {}
    if q:
        crit = {"squad_id": {"$regex": q, "$options": "i"}}
    items: list[Squad] = []
    cursor = dbase.squads.find(crit).sort("squad_id").skip(skip).limit(limit)
    async for doc in cursor:
        doc["_id"] = str(doc.get("_id"))
        items.append(Squad.model_validate(doc))
    return items


@router.get("/squads/{id_or_key}", response_model=Squad, summary="Get squad by id or key")
async def get_squad(id_or_key: str):
    s = await repo().get_squad(id_or_key)
    if not s:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return s


@router.patch("/squads/{squad_id}", response_model=Squad, summary="Update squad (partial)")
async def update_squad(squad_id: str, patch: dict, _=Depends(require_permissions("can_manage_roles"))):
    updated = await repo().update_squad(squad_id, patch)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return updated


@router.delete("/squads/{squad_id}", summary="Delete squad")
async def delete_squad(squad_id: str, _=Depends(require_permissions("can_manage_roles"))):
    deleted = await repo().delete_squad(squad_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"deleted": deleted}


@router.post("/jiraboards", response_model=JiraBoard, summary="Create JIRA board")
async def create_board(payload: JiraBoard, _=Depends(require_permissions("can_manage_roles"))):
    created = await repo().create_board(payload)
    if not created:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="board_id exists")
    return created


@router.get("/jiraboards", response_model=list[JiraBoard], summary="List JIRA boards")
async def list_boards(skip: int = Query(0, ge=0), limit: int = Query(50, gt=0, le=PAGE_SIZE_MAX), q: str | None = None):
    dbase = get_db()
    crit = {}
    if q:
        crit = {"board_id": {"$regex": q, "$options": "i"}}
    items: list[JiraBoard] = []
    cursor = dbase.jiraboards.find(crit).sort("board_id").skip(skip).limit(limit)
    async for doc in cursor:
        doc["_id"] = str(doc.get("_id"))
        items.append(JiraBoard.model_validate(doc))
    return items


@router.get("/jiraboards/{id_or_key}", response_model=JiraBoard, summary="Get JIRA board by id or key")
async def get_board(id_or_key: str):
    b = await repo().get_board(id_or_key)
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return b


@router.patch("/jiraboards/{board_id}", response_model=JiraBoard, summary="Update JIRA board (partial)")
async def update_board(board_id: str, patch: dict, _=Depends(require_permissions("can_manage_roles"))):
    updated = await repo().update_board(board_id, patch)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return updated


@router.delete("/jiraboards/{board_id}", summary="Delete JIRA board")
async def delete_board(board_id: str, _=Depends(require_permissions("can_manage_roles"))):
    deleted = await repo().delete_board(board_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"deleted": deleted}
