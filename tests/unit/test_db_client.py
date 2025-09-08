import pytest

from types import SimpleNamespace

import importlib


@pytest.mark.asyncio
async def test_db_client_connect_close_and_get(monkeypatch):
    # Import module fresh to reset state
    client_mod = importlib.import_module("app.db.client")

    # Ensure clean state
    monkeypatch.setattr(client_mod, "_client", None, raising=True)
    monkeypatch.setattr(client_mod, "_db", None, raising=True)

    created = {}

    class _FakeClient:
        def __init__(self, uri):  # noqa: ARG002
            created["count"] = created.get("count", 0) + 1
        def __getitem__(self, name):
            return SimpleNamespace(name=name)
        def close(self):
            created["closed"] = True

    # Patch motor client class
    monkeypatch.setattr(client_mod, "AsyncIOMotorClient", _FakeClient, raising=True)

    # First connect
    await client_mod.connect_to_mongo()
    assert created.get("count") == 1
    assert client_mod._client is not None
    assert client_mod._db is not None

    # Idempotent connect (should not create again)
    await client_mod.connect_to_mongo()
    assert created.get("count") == 1

    # get_db returns db
    db = client_mod.get_db()
    assert getattr(db, "name", None) is not None

    # Close
    await client_mod.close_mongo_connection()
    assert created.get("closed") is True
    assert client_mod._client is None
    assert client_mod._db is None

    # get_db should assert when no db
    with pytest.raises(AssertionError):
        client_mod.get_db()
