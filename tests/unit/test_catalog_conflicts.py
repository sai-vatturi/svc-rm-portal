import pytest
from httpx import AsyncClient
from fastapi import status

from app.main import app
from app.models.catalog import Application, Squad, JiraBoard

@pytest.mark.asyncio
async def test_catalog_create_conflicts(monkeypatch):
    # Fake repo to simulate duplicate returns None
    class FakeRepo:
        def __init__(self):
            self.calls = []
        async def create_application(self, payload):
            self.calls.append(("app", payload.application_id))
            return None  # simulate duplicate
        async def create_squad(self, payload):
            return None
        async def create_board(self, payload):
            return None
    fake = FakeRepo()
    from app.routers import catalog as cat
    monkeypatch.setattr(cat, "repo", lambda: fake)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        r1 = await ac.post("/catalog/applications", json={"application_id":"A1","name":"App1"})
        r2 = await ac.post("/catalog/squads", json={"squad_id":"S1","name":"Squad1"})
        r3 = await ac.post("/catalog/jiraboards", json={"board_id":"B1","name":"Board1","type":"kanban"})
    assert r1.status_code == status.HTTP_409_CONFLICT
    assert r2.status_code == status.HTTP_409_CONFLICT
    assert r3.status_code == status.HTTP_409_CONFLICT
    body = r1.json()
    assert body["error"]["code"] == "CONFLICT"

