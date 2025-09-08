import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.rbac import Role, User
from app.utils.time import utcnow


@pytest.mark.asyncio
async def test_roles_create_and_list(monkeypatch):
    # grant permission
    from app.core import security as sec

    class _P:
        permissions = {"can_manage_roles": True}

    app.dependency_overrides[sec.get_current_user] = lambda: _P()

    created = []
    roles_list = [Role(_id="r1", role_name="A", created_at=utcnow())]

    class _Repo:
        async def create_role(self, role: Role):  # noqa: ARG002
            created.append(1)
            return Role(_id="r2", role_name="B", created_at=utcnow())

        async def list_roles(self):
            return roles_list

    from app.routers import rbac as mod
    monkeypatch.setattr(mod, "repo", lambda: _Repo())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/rbac/roles",
            json={"role_name": "X", "created_at": "2025-01-01T00:00:00+00:00"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["role_name"] == "B"

        resp2 = await ac.get("/rbac/roles")
        assert resp2.status_code == 200
        assert len(resp2.json()) == 1

    app.dependency_overrides.pop(sec.get_current_user, None)


@pytest.mark.asyncio
async def test_users_create_get_and_me(monkeypatch):
    # grant permission for create_user and provide principal for /rbac/me
    from app.core import security as sec

    class _P:
        permissions = {"can_manage_roles": True}
        user = type(
            "U",
            (),
            {"id": "u1", "username": "jdoe", "full_name": "Jane Doe", "email": "jdoe@example.com"},
        )()
        role_names = ["Manager"]

    app.dependency_overrides[sec.get_current_user] = lambda: _P()

    user_obj = User(
        _id="u1",
        username="jdoe",
        full_name="Jane Doe",
        email="jdoe@example.com",
        password_hash="h",
        role_ids=[],
        assigned_squad_ids=[],
        created_at=utcnow(),
    )

    class _Repo:
        async def find_user_by_id(self, uid: str):
            return user_obj if uid == "u1" else None

    class _AuthSvc:
        async def register_user(self, payload):  # noqa: ARG002
            return user_obj

    from app.routers import rbac as mod
    monkeypatch.setattr(mod, "repo", lambda: _Repo())
    # Proper FastAPI dependency override for Depends(auth_service)
    app.dependency_overrides[mod.auth_service] = lambda: _AuthSvc()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # create user
        payload = {
            "username": "jdoe",
            "full_name": "Jane Doe",
            "email": "jdoe@example.com",
            "password": "x",
            "role_ids": [],
        }
        r1 = await ac.post("/rbac/users", json=payload)
        assert r1.status_code == 200
        # get user not found
        rnf = await ac.get("/rbac/users/u2")
        assert rnf.status_code == 404
        # get user ok
        rok = await ac.get("/rbac/users/u1")
        assert rok.status_code == 200
        # me
        me = await ac.get("/rbac/me")
        assert me.status_code == 200
        body = me.json()
        assert body["username"] == "jdoe"
        assert "permissions" in body

    app.dependency_overrides.pop(sec.get_current_user, None)
    app.dependency_overrides.pop(mod.auth_service, None)
