import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId

from app.main import app


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)
    def sort(self, field, direction):
        reverse = direction == -1
        try:
            self._docs.sort(key=lambda d: d.get(field), reverse=reverse)
        except Exception:
            pass
        return self
    def limit(self, n):
        self._docs = self._docs[:n]
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
        if "$push" in update:
            path, value = next(iter(update["$push"].items()))
            if path == "products":
                doc.setdefault("products", []).append(value)
                _Res.modified_count = 1
            elif path == "attachment_refs":
                doc.setdefault("attachment_refs", []).append(value)
                _Res.modified_count = 1
            elif path == "runbooks":
                doc.setdefault("runbooks", []).append(value)
                _Res.modified_count = 1
            elif path.startswith("products.$[p].quality_gates"):
                if path.endswith("quality_gates"):
                    pid = None
                    for f in (array_filters or []):
                        if "p.product_id" in f:
                            pid = f["p.product_id"]
                    if pid is None:
                        return _Res()
                    for p in doc.setdefault("products", []):
                        if p.get("product_id") == pid:
                            p.setdefault("quality_gates", []).append(value)
                            _Res.modified_count = 1
                            break
                elif path.endswith("milestones"):
                    pid = None
                    gname = None
                    for f in (array_filters or []):
                        if "p.product_id" in f:
                            pid = f["p.product_id"]
                        if "g.gate_name" in f:
                            gname = f["g.gate_name"]
                    if pid is None or gname is None:
                        return _Res()
                    for p in doc.setdefault("products", []):
                        if p.get("product_id") == pid:
                            for g in p.setdefault("quality_gates", []):
                                if g.get("gate_name") == gname:
                                    g.setdefault("milestones", []).append(value)
                                    _Res.modified_count = 1
                                    break
        if "$set" in update:
            for k, v in update["$set"].items():
                doc[k] = v
            _Res.modified_count = 1
        return _Res()


class _DB:
    def __init__(self):
        self.releases = _Releases()


@pytest.mark.asyncio
async def test_release_router_happy_path(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()

    # Grant all perms via get_current_user override
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

    # Patch DB
    from app.routers import release as mod
    _db = _DB()
    monkeypatch.setattr(mod, "get_db", lambda: _db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # create
        payload = {
            "release_id": "REL-1",
            "release_name": "R1",
            "release_date": now,
            "created_at": now,
            "products": [],
            "attachment_refs": []
        }
        r = await ac.post("/releases", json=payload)
        assert r.status_code == 200
        rel = r.json()
        rid = rel.get("id") or rel.get("_id")
        assert rid

        # list
        l = await ac.get("/releases", params={"limit": 10})
        assert l.status_code == 200
        body = l.json()
        assert len(body["items"]) >= 1
        assert body["next_cursor"] is not None

        # get by id
        g = await ac.get(f"/releases/{rid}")
        assert g.status_code == 200
        assert g.json()["release_id"] == "REL-1"

        # get by key
        gk = await ac.get("/releases/REL-1")
        assert gk.status_code == 200
        assert gk.json()["release_name"] == "R1"

        # update description
        u = await ac.patch(f"/releases/{rid}/description", json={"description": "updated"})
        assert u.status_code == 200
        assert u.json()["description"] == "updated"

        # add product
        p = await ac.post(f"/releases/{rid}/products", json={"application_id": "app1", "product_id": "p1"})
        assert p.status_code == 200
        assert any(prod["product_id"] == "p1" for prod in p.json().get("products", []))

        # add gate
        g2 = await ac.post(f"/releases/{rid}/products/p1/gates", json={"gate_name": "QA"})
        assert g2.status_code == 200
        prods = g2.json().get("products", [])
        assert prods and prods[0].get("quality_gates")

        # add milestone
        m = await ac.post(f"/releases/{rid}/products/p1/gates/QA/milestones", json={"milestone_key": "MS1", "milestone_name": "UAT"})
        assert m.status_code == 200
        gates = m.json().get("products", [])[0].get("quality_gates", [])
        assert gates and gates[0].get("milestones")

        # approve milestone
        ap = await ac.post(f"/releases/{rid}/products/p1/gates/QA/milestones/MS1/approve", json={"comment": "ok"})
        assert ap.status_code == 200

        # upsert change
        ch = await ac.patch(f"/releases/{rid}/change", json={"change_id": "CHG-1"})
        assert ch.status_code == 200
        assert ch.json().get("chg", {}).get("change_id") == "CHG-1"

        # attach
        a = await ac.post(f"/releases/{rid}/attachments", json={"attachment_id": "att1"})
        assert a.status_code == 200
        assert len(a.json().get("attachment_refs", [])) == 1

        # add runbook
        rb = await ac.post(f"/releases/{rid}/runbooks", json={"runbook_id": "rb1", "runbook_name": "RB"})
        assert rb.status_code == 200
        assert len(rb.json().get("runbooks", [])) == 1

        # update runbook task
        urt = await ac.patch(f"/releases/{rid}/runbooks/rb1/tasks/T1", json={"status": "DONE"})
        assert urt.status_code == 200

        # summary
        s = await ac.get(f"/releases/{rid}/summary")
        assert s.status_code == 200
        sj = s.json()
        assert "gate_status_counts" in sj and "flags" in sj

    app.dependency_overrides.pop(sec.get_current_user, None)
