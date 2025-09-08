import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId
from datetime import datetime

from app.main import app


class _Cursor:
    def __init__(self, docs):
        self._docs = docs
    def sort(self, *_):
        return self
    def limit(self, *_):
        return self
    def __aiter__(self):
        async def _gen():
            for d in self._docs:
                yield d
        return _gen()


@pytest.mark.asyncio
async def test_list_attachments_pagination(monkeypatch):
    # fake db with two valid items
    now = datetime.utcnow().isoformat() + "Z"
    docs = [
        {"_id": ObjectId(), "file_name": "a.txt", "file_type": "text/plain", "file_size": 1, "file_url": "http://x/a.txt", "sha256": "aa", "tags": [], "uploaded_at": now, "links": []},
        {"_id": ObjectId(), "file_name": "b.txt", "file_type": "text/plain", "file_size": 2, "file_url": "http://x/b.txt", "sha256": "bb", "tags": [], "uploaded_at": now, "links": []},
    ]
    class _FakeAttachments:
        def find(self, filters):  # noqa: ARG002
            return _Cursor(docs)
    class _FakeDB:
        attachments = _FakeAttachments()
    from app.routers import attachments as mod
    monkeypatch.setattr(mod, "get_db", lambda: _FakeDB())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/attachments", params={"limit": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    # next_cursor present when there are items
    assert data["next_cursor"]
