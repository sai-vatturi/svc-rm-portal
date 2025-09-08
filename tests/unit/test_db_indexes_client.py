import pytest

from app.db.client import get_db
from app.db.indexes import create_indexes


@pytest.mark.asyncio
async def test_get_db_assert_message(monkeypatch):
    # Force _db to None to hit assertion message
    import app.db.client as client
    client._db = None
    with pytest.raises(AssertionError) as ei:
        get_db()
    assert "Database is not initialized" in str(ei.value)


@pytest.mark.asyncio
async def test_create_indexes_uses_db(monkeypatch):
    created = []
    class _C:
        async def create_index(self, name, unique=False):  # noqa: ARG002
            created.append(name)
    class _DB:
        roles = _C(); users = _C(); applications = _C(); squads = _C(); jiraboards = _C(); releases = _C(); attachments = _C()
    import app.db.indexes as indexes_mod
    monkeypatch.setattr(indexes_mod, "get_db", lambda: _DB())

    await create_indexes()
    # spot-check a few
    assert "role_name" in created and "username" in created and "release_id" in created
