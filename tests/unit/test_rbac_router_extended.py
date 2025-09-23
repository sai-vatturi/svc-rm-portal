import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.utils.time import utcnow
from app.models.rbac import Role, User


@pytest.mark.asyncio
async def test_rbac_role_and_user_crud(monkeypatch):
    # Override principal with manage_roles permission
    from app.core import security as sec

    class _P:
        permissions = {"can_manage_roles": True}
        user = type("U", (), {"id": "admin"})()

    app.dependency_overrides[sec.get_current_user] = lambda: _P()

    # In-memory store
    roles: dict[str, Role] = {}
    users: dict[str, User] = {}

    from app.utils.time import utcnow as _utcnow

    class _Repo:
        async def create_role(self, role: Role):  # noqa: ARG002
            r = Role(_id="r1", role_name="Role1", created_at=_utcnow())
            roles[r.id] = r
            return r
        async def list_roles(self):
            return list(roles.values())
        async def get_role_by_id(self, rid: str):
            return roles.get(rid)
        async def update_role(self, rid: str, patch):  # noqa: ARG002
            r = roles.get(rid)
            if not r:
                return None
            data = r.model_dump()
            data.update({k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None})
            roles[rid] = Role(**{**data, "created_at": r.created_at})
            return roles[rid]
        async def delete_role(self, rid: str):
            return 1 if roles.pop(rid, None) else 0
        async def find_user_by_id(self, uid: str):
            return users.get(uid)
        async def list_users(self, skip=0, limit=50):  # noqa: ARG002
            return list(users.values())
        async def update_user(self, uid: str, patch):  # noqa: ARG002
            u = users.get(uid)
            if not u:
                return None
            data = u.model_dump()
            data.update({k: v for k, v in patch.model_dump(exclude_unset=True).items() if v is not None})
            users[uid] = User(**{**data, "created_at": u.created_at})
            return users[uid]
        async def delete_user(self, uid: str):
            return 1 if users.pop(uid, None) else 0

    class _AuthSvc:
        async def register_user(self, payload):  # noqa: ARG002
            u = User(_id="u1", username="user1", full_name="U One", email="u1@example.com", password_hash="h", role_ids=[], assigned_squad_ids=[], created_at=_utcnow())
            users[u.id] = u  # type: ignore[attr-defined]
            return u

    from app.routers import rbac as mod
    monkeypatch.setattr(mod, "repo", lambda: _Repo())
    app.dependency_overrides[mod.auth_service] = lambda: _AuthSvc()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Create role
        resp = await ac.post("/rbac/roles", json={"role_name": "Role1", "created_at": utcnow().isoformat()})
        assert resp.status_code == 200
        rid = resp.json()["id"]
        # Get role
        rg = await ac.get(f"/rbac/roles/{rid}")
        assert rg.status_code == 200
        # Patch role
        rp = await ac.patch(f"/rbac/roles/{rid}", json={"description": "updated"})
        assert rp.status_code == 200 and rp.json()["description"] == "updated"
        # List roles
        rl = await ac.get("/rbac/roles")
        assert rl.status_code == 200 and len(rl.json()) == 1
        # Create user
        cu = await ac.post("/rbac/users", json={"username": "user1", "full_name": "U One", "email": "u1@example.com", "password": "x", "role_ids": [], "created_at": utcnow().isoformat()})
        assert cu.status_code == 200
        uid = cu.json()["id"]
        # List users
        lu = await ac.get("/rbac/users")
        assert lu.status_code == 200 and len(lu.json()) == 1
        # Patch user
        pu = await ac.patch(f"/rbac/users/{uid}", json={"full_name": "User One"})
        assert pu.status_code == 200 and pu.json()["full_name"] == "User One"
        # Delete user
        du = await ac.delete(f"/rbac/users/{uid}")
        assert du.status_code == 200 and du.json()["deleted"] == 1
        # Delete role
        dr = await ac.delete(f"/rbac/roles/{rid}")
        assert dr.status_code == 200 and dr.json()["deleted"] == 1

    app.dependency_overrides.pop(sec.get_current_user, None)
    app.dependency_overrides.pop(mod.auth_service, None)
