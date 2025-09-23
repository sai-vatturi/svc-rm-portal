from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.pagination import PageQuery, Paginated, encode_cursor, try_decode_cursor
from app.core.security import get_current_user, require_permissions
from app.db.client import get_db
from app.models.common import AttachmentRef
from app.models.release import (
    ApproveMilestoneRequest,
    Release,
    ReleaseChange,
    ReleaseDescriptionUpdate,
    ReleaseMilestone,
    ReleaseProduct,
    ReleaseProductQualityGate,
    ReleaseRunbook,
    UpdateMilestone,
    UpdateQualityGate,
    UpdateRunbookTask,
)
from app.utils.time import utcnow

router = APIRouter()


@router.post("/releases", response_model=Release, summary="Create release")
async def create_release(payload: Release, principal=Depends(require_permissions("can_create_release"))):  # noqa: ARG001
    db = get_db()
    if await db.releases.find_one({"release_id": payload.release_id}):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="release_id exists")
    data = payload.model_dump(by_alias=True)
    res = await db.releases.insert_one(data)
    data["_id"] = str(res.inserted_id)
    return Release.model_validate(data)


@router.get("/releases", response_model=Paginated[Release], summary="List releases (paginated)")
async def list_releases(q: str | None = None, page: PageQuery = Depends()):
    db = get_db()
    filters: dict[str, Any] = {}
    if q:
        filters = {"$or": [{"release_id": {"$regex": q, "$options": "i"}}, {"release_name": {"$regex": q, "$options": "i"}}]}

    last_id = try_decode_cursor(page.cursor)
    if last_id:
        filters.update({"_id": {"$lt": last_id}})

    cursor = db.releases.find(filters).sort("release_date", -1).limit(page.limit)
    items: list[Release] = []
    last = None
    async for doc in cursor:
        last = doc["_id"]
        doc["_id"] = str(doc["_id"])
        items.append(Release.model_validate(doc))

    next_cursor = encode_cursor(last) if last else None
    return Paginated[Release](items=items, next_cursor=next_cursor)


@router.get("/releases/{id_or_key}", response_model=Release, summary="Get release by id or key")
async def get_release(id_or_key: str):
    db = get_db()
    doc = None
    try:
        doc = await db.releases.find_one({"_id": ObjectId(id_or_key)})
    except Exception:
        doc = await db.releases.find_one({"release_id": id_or_key})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.patch("/releases/{id}/description", response_model=Release, summary="Update release description")
async def update_release_description(id: str, payload: ReleaseDescriptionUpdate, _=Depends(require_permissions("can_edit_release_description"))):
    db = get_db()
    oid = ObjectId(id)
    await db.releases.update_one({"_id": oid}, {"$set": {"description": payload.description}})
    doc = await db.releases.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.post("/releases/{id}/products", response_model=Release, summary="Add product to release")
async def add_product(id: str, payload: ReleaseProduct, _=Depends(require_permissions("can_manage_quality_gates"))):
    db = get_db()
    oid = ObjectId(id)
    update = {"$push": {"products": payload.model_dump(by_alias=True)}}
    res = await db.releases.update_one({"_id": oid}, update)
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc = await db.releases.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.delete("/releases/{id}/products/{product_id}", response_model=Release, summary="Delete product")
async def delete_product(id: str, product_id: str, _=Depends(require_permissions("can_manage_quality_gates"))):
    db = get_db()
    oid = ObjectId(id)
    await db.releases.update_one({"_id": oid}, {"$pull": {"products": {"product_id": product_id}}})
    doc = await db.releases.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.post("/releases/{id}/products/{product_id}/gates", response_model=Release, summary="Add quality gate")
async def add_quality_gate(id: str, product_id: str, payload: ReleaseProductQualityGate, _=Depends(require_permissions("can_manage_quality_gates"))):
    db = get_db()
    oid = ObjectId(id)
    update = {"$push": {"products.$[p].quality_gates": payload.model_dump(by_alias=True)}}
    res = await db.releases.update_one({"_id": oid}, update, array_filters=[{"p.product_id": product_id}])
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release or product not found")
    doc = await db.releases.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.delete("/releases/{id}/products/{product_id}/gates/{gate_name}", response_model=Release, summary="Delete quality gate")
async def delete_quality_gate(id: str, product_id: str, gate_name: str, _=Depends(require_permissions("can_manage_quality_gates"))):
    db = get_db()
    oid = ObjectId(id)
    # Pull the gate from product
    await db.releases.update_one({"_id": oid, "products.product_id": product_id}, {"$pull": {"products.$.quality_gates": {"gate_name": gate_name}}})
    doc = await db.releases.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.patch("/releases/{id}/products/{product_id}/gates/{gate_name}", response_model=Release, summary="Update quality gate")
async def update_quality_gate(id: str, product_id: str, gate_name: str, payload: UpdateQualityGate, _=Depends(require_permissions("can_manage_quality_gates"))):
    db = get_db()
    oid = ObjectId(id)
    sets: dict[str, Any] = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        sets[f"products.$[p].quality_gates.$[g].{key}"] = value
    if not sets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    res = await db.releases.update_one({"_id": oid}, {"$set": sets}, array_filters=[{"p.product_id": product_id}, {"g.gate_name": gate_name}])
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release/product/gate not found")
    doc = await db.releases.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.post("/releases/{id}/products/{product_id}/gates/{gate_name}/milestones", response_model=Release, summary="Add milestone")
async def add_milestone(id: str, product_id: str, gate_name: str, payload: ReleaseMilestone, _=Depends(require_permissions("can_manage_quality_gates"))):
    db = get_db()
    oid = ObjectId(id)
    update = {"$push": {"products.$[p].quality_gates.$[g].milestones": payload.model_dump(by_alias=True)}}
    res = await db.releases.update_one({"_id": oid}, update, array_filters=[{"p.product_id": product_id}, {"g.gate_name": gate_name}])
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release/product/gate not found")
    doc = await db.releases.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.delete("/releases/{id}/products/{product_id}/gates/{gate_name}/milestones/{milestone_key}", response_model=Release, summary="Delete milestone")
async def delete_milestone(id: str, product_id: str, gate_name: str, milestone_key: str, _=Depends(require_permissions("can_manage_quality_gates"))):
    db = get_db()
    oid = ObjectId(id)
    await db.releases.update_one({"_id": oid, "products.product_id": product_id}, {"$pull": {"products.$.quality_gates.$[g].milestones": {"milestone_key": milestone_key}}}, array_filters=[{"g.gate_name": gate_name}])
    doc = await db.releases.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.patch("/releases/{id}/products/{product_id}/gates/{gate_name}/milestones/{milestone_key}", response_model=Release, summary="Update milestone")
async def update_milestone(id: str, product_id: str, gate_name: str, milestone_key: str, payload: UpdateMilestone, _=Depends(require_permissions("can_manage_quality_gates"))):
    db = get_db()
    oid = ObjectId(id)
    sets: dict[str, Any] = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        sets[f"products.$[p].quality_gates.$[g].milestones.$[m].{key}"] = value
    if not sets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    res = await db.releases.update_one(
        {"_id": oid},
        {"$set": sets},
        array_filters=[{"p.product_id": product_id}, {"g.gate_name": gate_name}, {"m.milestone_key": milestone_key}],
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Release/product/gate/milestone not found")
    doc = await db.releases.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.post("/releases/{id}/products/{product_id}/gates/{gate_name}/milestones/{milestone_key}/approve", response_model=Release, summary="Approve milestone")
async def approve_milestone(id: str, product_id: str, gate_name: str, milestone_key: str, payload: ApproveMilestoneRequest | None = None, principal=Depends(get_current_user)):
    db = get_db()
    oid = ObjectId(id)
    # Load release to inspect approval requirements
    doc = await db.releases.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Find milestone
    def _find_milestone(release_doc: dict) -> dict | None:
        for p in release_doc.get("products", []):
            if p.get("product_id") != product_id:
                continue
            for g in p.get("quality_gates", []):
                if g.get("gate_name") != gate_name:
                    continue
                for m in g.get("milestones", []):
                    if m.get("milestone_key") == milestone_key:
                        return m
        return None

    milestone = _find_milestone(doc)
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")

    approval = milestone.get("approval") or {}
    if approval.get("required") and approval.get("requires_approval_manager"):
        if not principal.permissions.get("is_approval_manager", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval manager required")

    comment = (payload.comment if payload else None) if hasattr(payload, "comment") else None  # type: ignore[union-attr]
    sets = {
        "products.$[p].quality_gates.$[g].milestones.$[m].approval.status": "APPROVED",
        "products.$[p].quality_gates.$[g].milestones.$[m].approval.approved_at": utcnow(),
        "products.$[p].quality_gates.$[g].milestones.$[m].approval.approver_user_id": str(principal.user.id),
        "products.$[p].quality_gates.$[g].milestones.$[m].approval.approver_role_snapshot": ", ".join(principal.role_names),
    }
    if comment:
        sets["products.$[p].quality_gates.$[g].milestones.$[m].approval.comment"] = comment

    await db.releases.update_one(
        {"_id": oid},
        {"$set": sets},
        array_filters=[{"p.product_id": product_id}, {"g.gate_name": gate_name}, {"m.milestone_key": milestone_key}],
    )

    updated = await db.releases.find_one({"_id": oid})
    updated["_id"] = str(updated["_id"])
    return Release.model_validate(updated)


@router.post("/releases/{id}/runbooks", response_model=Release, summary="Add runbook")
async def add_runbook(id: str, payload: ReleaseRunbook, principal=Depends(require_permissions("can_manage_runbooks"))):
    db = get_db()
    oid = ObjectId(id)
    rb = payload.model_dump(by_alias=True)
    if not rb.get("created_at"):
        rb["created_at"] = utcnow()
    if principal and getattr(principal, "user", None):
        rb.setdefault("created_by", str(principal.user.id))
    res = await db.releases.update_one({"_id": oid}, {"$push": {"runbooks": rb}})
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc = await db.releases.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.get("/releases/{id}/runbooks", summary="List runbooks for a release")
async def list_runbooks(id: str):
    db = get_db()
    oid = ObjectId(id)
    doc = await db.releases.find_one({"_id": oid}, {"runbooks": 1})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return doc.get("runbooks", [])


@router.delete("/releases/{id}/runbooks/{runbook_id}", response_model=Release, summary="Delete runbook")
async def delete_runbook(id: str, runbook_id: str, _=Depends(require_permissions("can_manage_runbooks"))):
    db = get_db()
    oid = ObjectId(id)
    await db.releases.update_one({"_id": oid}, {"$pull": {"runbooks": {"runbook_id": runbook_id}}})
    doc = await db.releases.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.patch("/releases/{id}/runbooks/{runbook_id}/tasks/{task_name}", response_model=Release, summary="Update runbook task")
async def update_runbook_task(id: str, runbook_id: str, task_name: str, payload: UpdateRunbookTask, _=Depends(require_permissions("can_manage_runbooks"))):
    db = get_db()
    oid = ObjectId(id)
    sets: dict[str, Any] = {}
    for key, value in payload.model_dump(exclude_unset=True).items():
        sets[f"runbooks.$[rb].tasks.$[t].{key}"] = value
    if not sets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    res = await db.releases.update_one(
        {"_id": oid},
        {"$set": sets},
        array_filters=[{"rb.runbook_id": runbook_id}, {"t.task_name": task_name}],
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Runbook/task not found")
    doc = await db.releases.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.patch("/releases/{id}/change", response_model=Release, summary="Upsert release change")
async def upsert_change(id: str, payload: ReleaseChange, _=Depends(require_permissions("can_manage_quality_gates"))):
    db = get_db()
    oid = ObjectId(id)
    res = await db.releases.update_one({"_id": oid}, {"$set": {"chg": payload.model_dump(by_alias=True)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc = await db.releases.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.get("/releases/{id}/change", summary="Get release change section")
async def get_change(id: str):
    db = get_db()
    oid = ObjectId(id)
    doc = await db.releases.find_one({"_id": oid}, {"chg": 1})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return doc.get("chg") or {}


@router.post("/releases/{id}/attachments", response_model=Release, summary="Attach attachment to release")
async def attach_to_release(id: str, payload: AttachmentRef, _=Depends(require_permissions("can_upload_attachments"))):
    db = get_db()
    oid = ObjectId(id)
    res = await db.releases.update_one({"_id": oid}, {"$push": {"attachment_refs": payload.model_dump(by_alias=True)}})
    if res.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc = await db.releases.find_one({"_id": oid})
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.delete("/releases/{id}/attachments/{sha256}", response_model=Release, summary="Remove attachment ref from release")
async def delete_release_attachment(id: str, sha256: str, _=Depends(require_permissions("can_upload_attachments"))):
    db = get_db()
    oid = ObjectId(id)
    await db.releases.update_one({"_id": oid}, {"$pull": {"attachment_refs": {"sha256": sha256}}})
    doc = await db.releases.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    doc["_id"] = str(doc["_id"])
    return Release.model_validate(doc)


@router.get("/releases/{id}/summary", summary="Computed release summary")
async def release_summary(id: str):
    db = get_db()
    oid = ObjectId(id)
    doc = await db.releases.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    # Compute summary
    gates = []
    milestones = []
    for p in doc.get("products", []):
        for g in p.get("quality_gates", []):
            gates.append(g)
            for m in g.get("milestones", []):
                milestones.append(m)

    gate_counts: dict[str, int] = {}
    for g in gates:
        status_val = (g.get("gate_status") or "NOT_STARTED").upper()
        gate_counts[status_val] = gate_counts.get(status_val, 0) + 1

    has_blockers = any((g.get("gate_status") in ["BLOCKED", "FAILED"] for g in gates)) or any(
        (m.get("status") in ["BLOCKED", "FAILED"] for m in milestones)
    )

    all_required_passed = True
    for g in gates:
        if g.get("required", True) and g.get("gate_status") != "PASSED":
            all_required_passed = False
            break

    # Next pending milestones (not DONE), ordered by start_date
    pending = [m for m in milestones if (m.get("status") not in ["DONE", "APPROVED"])]
    pending.sort(key=lambda x: x.get("start_date") or datetime.max)
    next_pending = [m.get("milestone_key") for m in pending[:5]]

    return {
        "gate_status_counts": gate_counts,
        "next_pending_milestone_keys": next_pending,
        "flags": {
            "all_required_gates_passed": all_required_passed,
            "has_blockers": has_blockers,
            "is_ready_for_approval": all_required_passed and not has_blockers,
        },
    }
