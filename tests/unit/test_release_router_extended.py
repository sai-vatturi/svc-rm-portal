import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId

from app.main import app


@pytest.mark.asyncio
async def test_release_delete_and_extras(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    from app.core import security as sec
    class _P:
        permissions = {
            "can_create_release": True,
            "can_manage_quality_gates": True,
            "can_upload_attachments": True,
            "can_manage_runbooks": True,
            "is_approval_manager": True,
            "can_edit_release_description": True,
        }
        user = type("U", (), {"id": "u1"})()
        role_names = ["Admin"]
    app.dependency_overrides[sec.get_current_user] = lambda: _P()

    # minimal in-memory db
    class _Releases:
        def __init__(self): self._store = {}
        async def find_one(self, q):
            if "_id" in q: return self._store.get(q["_id"]) or None
            if "release_id" in q:
                for d in self._store.values():
                    if d.get("release_id") == q["release_id"]: return d
            return None
        async def insert_one(self, data):
            oid = ObjectId()
            doc = {**data, "_id": oid}
            self._store[oid] = doc
            class _R: inserted_id = oid
            return _R()
        def find(self, filters):  # noqa: ARG002
            class _Cursor:
                def __init__(self, docs): self._docs = list(docs)
                def sort(self, *_): return self
                def limit(self, *_): return self
                def __aiter__(self):
                    async def _gen():
                        for d in self._docs: yield d
                    return _gen()
            return _Cursor(self._store.values())
        async def update_one(self, q, update, array_filters=None):  # noqa: ARG002
            oid = q.get("_id")
            doc = self._store.get(oid)
            class _Res: matched_count = 0; modified_count = 0
            if not doc: return _Res()
            _Res.matched_count = 1
            if "$push" in update:
                for k, v in update["$push"].items():
                    if k == "products": doc.setdefault("products", []).append(v)
                    elif k == "attachment_refs": doc.setdefault("attachment_refs", []).append(v)
                    elif k == "runbooks": doc.setdefault("runbooks", []).append(v)
                    elif k.startswith("products.$[p].quality_gates"):
                        # simplified; not fully simulating nested pushes
                        doc.setdefault("products", [])
            if "$set" in update:
                # naive set
                for k, v in update["$set"].items(): doc[k] = v
            if "$pull" in update:
                for k, v in update["$pull"].items():
                    if k == "products":
                        doc["products"] = [p for p in doc.get("products", []) if p.get("product_id") != v.get("product_id")]
                    elif k == "runbooks":
                        doc["runbooks"] = [rb for rb in doc.get("runbooks", []) if rb.get("runbook_id") != v.get("runbook_id")]
                    elif k == "attachment_refs":
                        doc["attachment_refs"] = [a for a in doc.get("attachment_refs", []) if a.get("sha256") != v.get("sha256")]
            return _Res()

    class _DB: releases = _Releases()

    from app.routers import release as mod
    monkeypatch.setattr(mod, "get_db", lambda: _DB())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"release_id": "REL-Z", "release_name": "RZ", "release_date": now, "created_at": now, "products": [], "attachment_refs": []}
        cr = await ac.post("/releases", json=payload)
        rid = cr.json()["id"]
        # Add product then delete
        await ac.post(f"/releases/{rid}/products", json={"application_id": "app1", "product_id": "p1"})
        dp = await ac.delete(f"/releases/{rid}/products/p1")
        assert dp.status_code in (200, 404)
        # Add runbook then delete
        await ac.post(f"/releases/{rid}/runbooks", json={"runbook_id": "rb1", "runbook_name": "RB"})
        drb = await ac.delete(f"/releases/{rid}/runbooks/rb1")
        assert drb.status_code in (200, 404)
        # Attach then remove
        await ac.post(f"/releases/{rid}/attachments", json={"attachment_id": "att1", "sha256": "sha"})
        da = await ac.delete(f"/releases/{rid}/attachments/sha")
        assert da.status_code in (200, 404)
        # Change section get after upsert
        await ac.patch(f"/releases/{rid}/change", json={"change_id": "C1"})
        gc = await ac.get(f"/releases/{rid}/change")
        assert gc.status_code == 200
        # Runbooks list
        lr = await ac.get(f"/releases/{rid}/runbooks")
        assert lr.status_code == 200

    app.dependency_overrides.pop(sec.get_current_user, None)
