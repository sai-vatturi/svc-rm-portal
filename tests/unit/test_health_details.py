import pytest
from httpx import AsyncClient
from fastapi import status

from app.main import app

@pytest.mark.asyncio
async def test_health_details(monkeypatch):
    # Monkeypatch get_db to fake minimal interface
    class _FakeColl:
        async def index_information(self):
            return {"_id_": {}}
    class _FakeDB(dict):
        async def command(self, cmd):
            assert cmd == "ping"
            return {"ok": 1}
    fake_db = _FakeDB()
    for c in ["users","roles","applications","squads","jiraboards","releases","attachments"]:
        fake_db[c] = _FakeColl()

    from app import db as dbpkg  # type: ignore
    from app.db import client as cl
    monkeypatch.setattr(cl, "get_db", lambda: fake_db)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health/details")
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["db"] == "up"
    assert "applications" in body["indexes"]

