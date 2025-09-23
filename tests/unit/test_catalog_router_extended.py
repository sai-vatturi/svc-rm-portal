import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId

from app.main import app


@pytest.mark.asyncio
async def test_catalog_crud(monkeypatch):
    # Permission principal
    from app.core import security as sec
    class _P:
        permissions = {"can_manage_roles": True}
    app.dependency_overrides[sec.get_current_user] = lambda: _P()

    # Simple in-memory stores
    apps: dict[str, dict] = {}
    squads_store: dict[str, dict] = {}
    boards_store: dict[str, dict] = {}

    class _Collection:
        def __init__(self, store, key_field):
            self.store = store
            self.key_field = key_field
        async def find_one(self, q):
            if "_id" in q:
                return self.store.get(q["_id"]) or None
            k = list(q.values())[0]
            for v in self.store.values():
                if v.get(self.key_field) == k:
                    return v
            return None
        async def insert_one(self, data):
            oid = str(ObjectId())
            doc = {**data, "_id": oid}
            self.store[oid] = doc
            class _Res: inserted_id = oid
            return _Res()
        async def delete_one(self, q):
            oid = q.get("_id")
            existed = 1 if self.store.pop(oid, None) else 0
            class _Res: deleted_count = existed
            return _Res()
        async def update_one(self, q, update):  # noqa: ARG002
            oid = q.get("_id")
            if oid not in self.store:
                return type("_R", (), {"matched_count": 0})()
            if "$set" in update:
                self.store[oid].update(update["$set"])
            return type("_R", (), {"matched_count": 1})()
        def find(self):
            class _Cursor:
                def __init__(self, items): self._items = list(items)
                def sort(self, *_): return self
                def __aiter__(self):
                    async def _gen():
                        for i in self._items: yield i
                    return _gen()
            return _Cursor(self.store.values())

    class _DB:
        applications = _Collection(apps, "application_id")
        squads = _Collection(squads_store, "squad_id")
        jiraboards = _Collection(boards_store, "board_id")

    from app.routers import catalog as mod
    monkeypatch.setattr(mod, "get_db", lambda: _DB())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # create app
        r1 = await ac.post("/catalog/applications", json={"application_id": "A1", "application_name": "App", "technologies": [], "products": []})
        assert r1.status_code == 200
        aid = r1.json()["id"]
        # get app
        rg = await ac.get(f"/catalog/applications/{aid}")
        assert rg.status_code == 200
        # patch app
        rp = await ac.patch(f"/catalog/applications/{aid}", json={"description": "desc"})
        assert rp.status_code == 200 and rp.json()["description"] == "desc"
        # delete app
        rd = await ac.delete(f"/catalog/applications/{aid}")
        assert rd.status_code == 200

        # squad
        s1 = await ac.post("/catalog/squads", json={"squad_id": "S1", "squad_name": "Squad", "squad_jira_board_ids": [], "member_ids": []})
        assert s1.status_code == 200
        sid = s1.json()["id"]
        sg = await ac.get(f"/catalog/squads/{sid}")
        assert sg.status_code == 200
        sp = await ac.patch(f"/catalog/squads/{sid}", json={"squad_name": "SquadX"})
        assert sp.status_code == 200 and sp.json()["squad_name"] == "SquadX"
        sd = await ac.delete(f"/catalog/squads/{sid}")
        assert sd.status_code == 200

        # board
        b1 = await ac.post("/catalog/jiraboards", json={"board_id": "B1", "board_name": "Board", "board_type": "scrum"})
        assert b1.status_code == 200
        bid = b1.json()["id"]
        bg = await ac.get(f"/catalog/jiraboards/{bid}")
        assert bg.status_code == 200
        bp = await ac.patch(f"/catalog/jiraboards/{bid}", json={"board_name": "BoardX"})
        assert bp.status_code == 200 and bp.json()["board_name"] == "BoardX"
        bd = await ac.delete(f"/catalog/jiraboards/{bid}")
        assert bd.status_code == 200

    app.dependency_overrides.pop(sec.get_current_user, None)
