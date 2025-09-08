import pytest

from app.services.rbac_service import AuthService
from app.models.rbac import User, UserCreate
from app.utils.time import utcnow


class _FakeRepoNone:
    async def find_user_by_username(self, username: str):
        return None


class _FakeRepoUser:
    def __init__(self, user: User):
        self._user = user

    async def find_user_by_username(self, username: str):
        return self._user

    async def create_user(self, user: User):
        # Simulate DB assigning an id and returning the saved user
        user.id = "uid-1"
        return user


@pytest.mark.asyncio
async def test_authenticate_returns_none_when_user_not_found(monkeypatch):
    svc = AuthService()
    monkeypatch.setattr(svc, "_repo", lambda: _FakeRepoNone())
    # Should not matter what verify_password does if user missing
    result = await svc.authenticate("ghost", "irrelevant")
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_returns_none_when_password_invalid(monkeypatch):
    from app.services import rbac_service as rs

    u = User(
        _id="user-id",
        username="jdoe",
        full_name="Jane Doe",
        email="jdoe@example.com",
        password_hash="hashed",
        role_ids=[],
        assigned_squad_ids=[],
        created_at=utcnow(),
    )
    svc = AuthService()
    monkeypatch.setattr(svc, "_repo", lambda: _FakeRepoUser(u))
    monkeypatch.setattr(rs, "verify_password", lambda p, h: False)

    result = await svc.authenticate("jdoe", "wrong")
    assert result is None


@pytest.mark.asyncio
async def test_authenticate_success_returns_tokenpair(monkeypatch):
    from app.services import rbac_service as rs

    u = User(
        _id="user-id",
        username="jdoe",
        full_name="Jane Doe",
        email="jdoe@example.com",
        password_hash="hashed",
        role_ids=[],
        assigned_squad_ids=[],
        created_at=utcnow(),
    )
    svc = AuthService()
    monkeypatch.setattr(svc, "_repo", lambda: _FakeRepoUser(u))
    monkeypatch.setattr(rs, "verify_password", lambda p, h: True)
    monkeypatch.setattr(rs, "create_access_token", lambda sub: "ACCESS")
    monkeypatch.setattr(rs, "create_refresh_token", lambda sub: "REFRESH")

    result = await svc.authenticate("jdoe", "correct")
    assert result is not None
    assert result.access_token == "ACCESS"
    assert result.refresh_token == "REFRESH"
    assert result.token_type == "bearer"


@pytest.mark.asyncio
async def test_register_user_hashes_and_calls_repo(monkeypatch):
    from app.services import rbac_service as rs

    created_holder = {"user": None}

    class _RepoCapture:
        async def create_user(self, user: User):
            created_holder["user"] = user
            user.id = "uid-123"
            return user

    svc = AuthService()
    monkeypatch.setattr(svc, "_repo", lambda: _RepoCapture())
    monkeypatch.setattr(rs, "hash_password", lambda p: "HASHED")

    payload = UserCreate(username="jdoe", full_name="Jane Doe", email="jdoe@example.com", password="secret", role_ids=[])
    out = await svc.register_user(payload)

    assert out.id == "uid-123"
    # Ensure password was hashed before passing to repo
    assert created_holder["user"].password_hash == "HASHED"
    # Ensure assigned arrays initialized
    assert created_holder["user"].assigned_squad_ids == []
    # created_at set
    assert created_holder["user"].created_at is not None
