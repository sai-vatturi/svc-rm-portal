from datetime import datetime
from bson import ObjectId
import pytest

from app.repositories.attachment_repo import AttachmentRepository
from app.models.attachment import Attachment


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
async def test_attachment_repo_upsert_and_list():
    now = datetime.now().isoformat() + "Z"

    class _AttCol:
        def __init__(self):
            self._store = {}
        async def find_one(self, q):  # noqa: ARG002
            sha = q.get("sha256")
            return self._store.get(sha)
        async def insert_one(self, data):
            self._store[data["sha256"]] = {**data, "_id": ObjectId()}
            class _Res:
                inserted_id = ObjectId()
            return _Res()
        def find(self, filters):  # noqa: ARG002
            docs = list(self._store.values())
            return _Cursor(docs)

    class _DB:
        attachments = _AttCol()

    repo = AttachmentRepository(_DB())

    a = Attachment(
        _id=None,
        file_name="a.txt",
        file_type="text/plain",
        file_size=1,
        file_url="http://x/a.txt",
        sha256="aa",
        tags=[],
        uploaded_at=now,
        links=[],
    )

    out1 = await repo.upsert_by_sha(a)
    assert out1.sha256 == "aa"

    # upsert returns existing
    out2 = await repo.upsert_by_sha(a)
    assert out2.sha256 == "aa"

    items, last = await repo.list_paginated(limit=10)
    assert len(items) == 1
    assert isinstance(last, ObjectId) or last is None
