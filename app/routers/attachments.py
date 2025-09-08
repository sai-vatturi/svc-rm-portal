from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.pagination import PageQuery, Paginated, encode_cursor, try_decode_cursor
from app.core.security import require_permissions
from app.db.client import get_db
from app.models.attachment import Attachment

router = APIRouter()


@router.post("/attachments", response_model=Attachment, summary="Create attachment metadata")
async def create_attachment(payload: Attachment, principal=Depends(require_permissions("can_upload_attachments"))):
    db = get_db()
    # Upsert by sha256 uniqueness
    exists = await db.attachments.find_one({"sha256": payload.sha256})
    if exists:
        exists["_id"] = str(exists.get("_id"))
        return Attachment.model_validate(exists)
    data = payload.model_dump(by_alias=True)
    res = await db.attachments.insert_one(data)
    data["_id"] = str(res.inserted_id)
    return Attachment.model_validate(data)


@router.get("/attachments", response_model=Paginated[Attachment], summary="List attachments (paginated)")
async def list_attachments(q: str | None = None, page: PageQuery = Depends()):
    db = get_db()
    filters = {}
    if q:
        filters = {"$or": [{"file_name": {"$regex": q, "$options": "i"}}, {"sha256": {"$regex": q, "$options": "i"}}]}

    last_id = try_decode_cursor(page.cursor)
    if last_id:
        filters.update({"_id": {"$lt": last_id}})

    cursor = db.attachments.find(filters).sort("_id", -1).limit(page.limit)
    items: list[Attachment] = []
    last = None
    async for doc in cursor:
        last = doc["_id"]
        doc["_id"] = str(doc["_id"])
        items.append(Attachment.model_validate(doc))

    next_cursor = encode_cursor(last) if last else None
    return Paginated[Attachment](items=items, next_cursor=next_cursor)
