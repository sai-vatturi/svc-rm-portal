import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime

from app.main import app


@pytest.mark.asyncio
async def test_create_attachment_insert_and_upsert(monkeypatch):
    # Grant permission
    from app.core import security as sec
    class _P:
        permissions = {"can_upload_attachments": True}
        user = type("U", (), {"id": "u1"})()
    app.dependency_overrides[sec.get_current_user] = lambda: _P()

    exists_flag = {"exists": False}

    class _Attachments:
        async def find_one(self, q):  # noqa: ARG002
            if exists_flag["exists"]:
                return {
                    "_id": "doc1",
                    "file_name": "a.txt",
                    "file_type": "text/plain",
                    "file_size": 1,
                    "file_url": "http://x/a.txt",
                    "sha256": "aa",
                    "tags": [],
                    "uploaded_at": datetime.now().isoformat() + "Z",
                    "links": [],
                }
            return None
        async def insert_one(self, data):  # noqa: ARG002
            class _Res:
                inserted_id = "doc1"
            return _Res()

    class _DB:
        attachments = _Attachments()

    from app.routers import attachments as mod
    monkeypatch.setattr(mod, "get_db", lambda: _DB())

    transport = ASGITransport(app=app)
    payload = {
        "file_name": "a.txt",
        "file_type": "text/plain",
        "file_size": 1,
        "file_url": "http://x/a.txt",
        "sha256": "aa",
        "tags": [],
        "uploaded_at": datetime.now().isoformat() + "Z",
        "links": [],
    }
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # insert path (no exists)
        resp = await ac.post("/attachments", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["_id"] == "doc1"
        # upsert path (exists)
        exists_flag["exists"] = True
        resp2 = await ac.post("/attachments", json=payload)
        assert resp2.status_code == 200
        body2 = resp2.json()
        assert body2["_id"] == "doc1"

    app.dependency_overrides.pop(sec.get_current_user, None)
