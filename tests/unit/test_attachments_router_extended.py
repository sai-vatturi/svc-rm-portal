import pytest
from httpx import AsyncClient, ASGITransport
from bson import ObjectId
from datetime import datetime

from app.main import app


@pytest.mark.asyncio
async def test_attachment_get_and_delete(monkeypatch):
    from app.core import security as sec
    class _P:
        permissions = {"can_upload_attachments": True}
    app.dependency_overrides[sec.get_current_user] = lambda: _P()

    now = datetime.utcnow().isoformat() + "Z"
    store = {}

    class _Attachments:
        async def find_one(self, q):
            oid = q.get("_id")
            return store.get(oid)
        async def delete_one(self, q):
            oid = q.get("_id")
            existed = 1 if store.pop(oid, None) else 0
            class _Res: deleted_count = existed
            return _Res()
        def find(self, filters):  # noqa: ARG002
            class _Cursor:
                def __init__(self, docs): self._docs = list(docs)
                def sort(self, *_): return self
                def limit(self, *_): return self
                def __aiter__(self):
                    async def _gen():
                        for d in self._docs: yield d
                    return _gen()
            return _Cursor(store.values())
        async def insert_one(self, data):
            oid = str(ObjectId())
            doc = {**data, "_id": oid}
            store[oid] = doc
            class _Res: inserted_id = oid
            return _Res()

    class _DB:
        attachments = _Attachments()

    from app.routers import attachments as mod
    monkeypatch.setattr(mod, "get_db", lambda: _DB())

    # seed one
    payload = {"file_name": "a.txt", "file_type": "text/plain", "file_size": 1, "file_url": "http://x/a.txt", "sha256": "sha1", "tags": [], "uploaded_at": now, "links": []}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        c = await ac.post("/attachments", json=payload)
        assert c.status_code == 200
        att_id = c.json()["id"]
        g = await ac.get(f"/attachments/{att_id}")
        assert g.status_code == 200
        d = await ac.delete(f"/attachments/{att_id}")
        assert d.status_code == 200 and d.json()["deleted"] == 1
        g404 = await ac.get(f"/attachments/{att_id}")
        assert g404.status_code == 404

    app.dependency_overrides.pop(sec.get_current_user, None)
