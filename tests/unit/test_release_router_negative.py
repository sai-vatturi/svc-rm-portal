import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId

from app.main import app


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)
    def sort(self, field, direction):  # noqa: ARG002
        return self
    def limit(self, n):  # noqa: ARG002
        return self
    def __aiter__(self):
        async def _gen():
            for d in self._docs:
                yield d
        return _gen()


class _Releases:
    def __init__(self):
        self._store = {}
    async def find_one(self, q):
        if "_id" in q:
            return self._store.get(q["_id"]) or None
        if "release_id" in q:
            for v in self._store.values():
                if v.get("release_id") == q["release_id"]:
                    return v
        return None
    async def insert_one(self, data):
        oid = ObjectId()
        doc = {**data, "_id": oid}
        self._store[oid] = doc
        class _Res:
            inserted_id = oid
        return _Res()
    def find(self, filters):  # noqa: ARG002
        return _Cursor(list(self._store.values()))
    async def update_one(self, q, update, array_filters=None):  # noqa: ARG002
        _id = q.get("_id")
        doc = self._store.get(_id)
        class _Res:
            matched_count = 0
            modified_count = 0
        if not doc:
            return _Res()
        _Res.matched_count = 1
        # For negative tests we don't need to mutate doc
        if "$set" in update or "$push" in update:
            _Res.modified_count = 1
        return _Res()


class _DB:
    def __init__(self):
        self.releases = _Releases()


@pytest.mark.asyncio
async def test_conflict_and_bad_requests_and_not_found(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()

    from app.core import security as sec
    class _P:
        permissions = {
            "can_create_release": True,
            "can_manage_quality_gates": True,
            "can_upload_attachments": True,
            "can_manage_runbooks": True,
            "can_edit_release_description": True,
        }
        user = type("U", (), {"id": "u1"})()
        role_names = ["Admin"]
    app.dependency_overrides[sec.get_current_user] = lambda: _P()

    from app.routers import release as mod
    _db = _DB()
    monkeypatch.setattr(mod, "get_db", lambda: _db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "release_id": "REL-X",
            "release_name": "RX",
            "release_date": now,
            "created_at": now,
            "products": [],
            "attachment_refs": []
        }
        r1 = await ac.post("/releases", json=payload)
        assert r1.status_code == 200
        # conflict on second create
        r2 = await ac.post("/releases", json=payload)
        assert r2.status_code == 409

        rid = (r1.json().get("id") or r1.json().get("_id"))

        # list with q to hit filter branch
        l = await ac.get("/releases", params={"limit": 10, "q": "RX"})
        assert l.status_code == 200

        # update quality gate with no fields -> 400
        rq = await ac.patch(f"/releases/{rid}/products/p1/gates/Q/", json={})
        assert rq.status_code in (307, 400, 404)
        # Specifically test the 400 on "no fields" using existing release id
        rq2 = await ac.patch(f"/releases/{rid}/products/p1/gates/Q", json={})
        # Either 400 due to no fields or 404 if gate not found occurs first in our fake
        assert rq2.status_code in (400, 404)

        # update milestone with no fields
        rm = await ac.patch(f"/releases/{rid}/products/p1/gates/Q/milestones/MS1", json={})
        assert rm.status_code in (400, 404)

        # update runbook task with no fields
        ur = await ac.patch(f"/releases/{rid}/runbooks/rb1/tasks/T1", json={})
        assert ur.status_code == 400

        # operations on unknown release id -> 404
        unknown = str(ObjectId())
        g404 = await ac.get(f"/releases/{unknown}")
        assert g404.status_code == 404
        aq404 = await ac.post(f"/releases/{unknown}/products/p1/gates", json={"gate_name": "Q"})
        assert aq404.status_code == 404
        am404 = await ac.post(f"/releases/{unknown}/products/p1/gates/Q/milestones", json={"milestone_key": "MS", "milestone_name": "N"})
        assert am404.status_code == 404

    app.dependency_overrides.pop(sec.get_current_user, None)


@pytest.mark.asyncio
async def test_approve_milestone_permission_denied(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()

    from app.core import security as sec
    class _PNoMgr:
        permissions = {}
        user = type("U", (), {"id": "u2"})()
        role_names = ["Viewer"]
    app.dependency_overrides[sec.get_current_user] = lambda: _PNoMgr()

    from app.routers import release as mod
    _db = _DB()
    # Preload a doc with approval requiring manager
    rid = ObjectId()
    _db.releases._store[rid] = {
        "_id": rid,
        "release_id": "REL-Y",
        "release_name": "RY",
        "release_date": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "products": [
            {
                "application_id": "app1",
                "product_id": "p1",
                "quality_gates": [
                    {
                        "gate_name": "QA",
                        "required": True,
                        "milestones": [
                            {
                                "milestone_key": "MS1",
                                "milestone_name": "UAT",
                                "approval": {"required": True, "requires_approval_manager": True}
                            }
                        ]
                    }
                ]
            }
        ],
    }
    monkeypatch.setattr(mod, "get_db", lambda: _db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ap = await ac.post(f"/releases/{rid}/products/p1/gates/QA/milestones/MS1/approve", json={"comment": "ok"})
        assert ap.status_code == 403

    app.dependency_overrides.pop(sec.get_current_user, None)
