import pytest

from app.repositories.release_repo import ReleaseRepository


@pytest.mark.asyncio
async def test_release_repo_get_by_id_and_update(monkeypatch):
    class _Col:
        async def find_one(self, q):  # noqa: ARG002
            return {"_id": "oid"}
        async def update_one(self, q, update):  # noqa: ARG002
            class _Res:
                modified_count = 1
            return _Res()
    class _DB:
        releases = _Col()

    repo = ReleaseRepository(_DB())
    doc = await repo.get_by_id("64f9b8c1f1e4a9fd1a2b3c4d")
    assert doc["_id"] == "oid"

    n = await repo.update("64f9b8c1f1e4a9fd1a2b3c4d", {"$set": {"x": 1}})
    assert n == 1
