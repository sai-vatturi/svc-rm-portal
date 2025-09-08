import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


class _Cursor:
    def __init__(self, items):
        self._items = items
    def sort(self, *_):
        return self
    def __aiter__(self):
        async def _gen():
            for i in self._items:
                yield i
        return _gen()


@pytest.mark.asyncio
async def test_list_catalog_endpoints_empty(monkeypatch):
    class _FakeDB:
        def __init__(self):
            self.applications = type("C", (), {"find": lambda self: _Cursor([])})()
            self.squads = type("C", (), {"find": lambda self: _Cursor([])})()
            self.jiraboards = type("C", (), {"find": lambda self: _Cursor([])})()

    from app.routers import catalog as cat
    monkeypatch.setattr(cat, "get_db", lambda: _FakeDB())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r1 = await ac.get("/catalog/applications")
        r2 = await ac.get("/catalog/squads")
        r3 = await ac.get("/catalog/jiraboards")
    assert r1.status_code == 200 and r1.json() == []
    assert r2.status_code == 200 and r2.json() == []
    assert r3.status_code == 200 and r3.json() == []


@pytest.mark.asyncio
async def test_create_application_conflict_and_success(monkeypatch):
    # Override get_current_user via dependency to satisfy permission
    from app.core import security as sec

    class _P:
        permissions = {"can_manage_roles": True}

    app.dependency_overrides[sec.get_current_user] = lambda: _P()

    exists_flag = {"exists": True}

    class _Apps:
        async def find_one(self, q):  # noqa: ARG002
            return {"_id": "x"} if exists_flag["exists"] else None
        async def insert_one(self, data):  # noqa: ARG002
            class _Res:
                inserted_id = "newid"
            return _Res()

    class _FakeDB:
        applications = _Apps()

    from app.routers import catalog as cat
    monkeypatch.setattr(cat, "get_db", lambda: _FakeDB())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # conflict
        payload = {"application_id": "APP1", "application_name": "A", "technologies": [], "products": []}
        r = await ac.post("/catalog/applications", json=payload)
        assert r.status_code == 409
        # success
        exists_flag["exists"] = False
        r2 = await ac.post("/catalog/applications", json=payload)
        assert r2.status_code == 200
        body = r2.json()
        assert body["_id"] == "newid"

    app.dependency_overrides.pop(sec.get_current_user, None)
