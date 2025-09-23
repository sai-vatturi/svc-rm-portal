import pytest
from jose import jwt

from app.core.security import (
    create_token,
    create_access_token,
    create_refresh_token,
    verify_password,
    hash_password,
    decode_token,
    get_current_user,
    require_permissions,
    CurrentPrincipal,
)
from app.core.config import settings
from app.models.rbac import User, Role
from app.utils.time import utcnow


def test_hash_and_verify_password_roundtrip():
    h = hash_password("s3cret!")
    assert isinstance(h, str)
    assert verify_password("s3cret!", h)
    assert not verify_password("wrong", h)


def test_token_helpers_and_decode():
    access = create_access_token("user-1")
    refresh = create_refresh_token("user-1")
    da = decode_token(access)
    dr = decode_token(refresh)
    assert da and da["sub"] == "user-1" and da["type"] == "access"
    assert dr and dr["sub"] == "user-1" and dr["type"] == "refresh"


def test_decode_token_invalid_returns_none():
    assert decode_token("not-a-jwt") is None


def test_decode_token_expired_returns_none():
    # make an already expired token
    payload = {"sub": "u", "type": "access", "iat": 0, "exp": 1}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    assert decode_token(token) is None


@pytest.mark.asyncio
async def test_get_current_user_missing_header_401():
    with pytest.raises(Exception) as ei:
        await get_current_user(None)  # type: ignore[arg-type]
    assert getattr(ei.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_type_refresh_token(monkeypatch):
    # Use a real refresh token so JWT is valid but wrong type
    token = create_refresh_token("u1")

    class _FakeRepo:
        async def find_user_by_id(self, uid: str):
            return None

        async def get_roles_by_ids(self, role_ids):
            return []

    from app.core import security as sec

    monkeypatch.setattr(sec, "RbacRepository", lambda db: _FakeRepo())
    monkeypatch.setattr(sec, "get_db", lambda: object())

    with pytest.raises(Exception) as ei:
        await get_current_user(f"Bearer {token}")  # type: ignore[arg-type]
    assert getattr(ei.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_get_current_user_missing_sub_401(monkeypatch):
    token = jwt.encode({"type": "access", "iat": 0, "exp": 32503680000}, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

    class _FakeRepo:
        async def find_user_by_id(self, uid: str):
            return None

        async def get_roles_by_ids(self, role_ids):
            return []

    from app.core import security as sec

    monkeypatch.setattr(sec, "RbacRepository", lambda db: _FakeRepo())
    monkeypatch.setattr(sec, "get_db", lambda: object())

    with pytest.raises(Exception) as ei:
        await get_current_user(f"Bearer {token}")  # type: ignore[arg-type]
    assert getattr(ei.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_get_current_user_user_not_found_401(monkeypatch):
    access = create_access_token("u1")

    class _FakeRepo:
        async def find_user_by_id(self, uid: str):
            return None

        async def get_roles_by_ids(self, role_ids):
            return []

    from app.core import security as sec

    monkeypatch.setattr(sec, "RbacRepository", lambda db: _FakeRepo())
    monkeypatch.setattr(sec, "get_db", lambda: object())

    with pytest.raises(Exception) as ei:
        await get_current_user(f"Bearer {access}")  # type: ignore[arg-type]
    assert getattr(ei.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_get_current_user_success_and_permissions_aggregate(monkeypatch):
    # Ensure enforcement ON so permissions reflect role flags instead of permissive grant
    prev = settings.RBAC_ENFORCEMENT_ENABLED
    settings.RBAC_ENFORCEMENT_ENABLED = True
    access = create_access_token("u1")

    u = User(
        _id="u1",
        username="u",
        full_name=None,
        email="u@example.com",
        password_hash="h",
        role_ids=["r1", "r2"],
        assigned_squad_ids=[],
        created_at=utcnow(),
    )
    r1 = Role(_id="r1", role_name="A", created_at=utcnow(), can_invite_users=True)
    r2 = Role(_id="r2", role_name="B", created_at=utcnow(), can_manage_roles=True)

    class _FakeRepo:
        async def find_user_by_id(self, uid: str):
            return u

        async def get_roles_by_ids(self, role_ids):
            return [r1, r2]

    from app.core import security as sec

    monkeypatch.setattr(sec, "RbacRepository", lambda db: _FakeRepo())
    monkeypatch.setattr(sec, "get_db", lambda: object())

    principal = await get_current_user(f"Bearer {access}")  # type: ignore[arg-type]
    assert principal.user.username == "u"
    assert principal.role_names == ["A", "B"]
    assert principal.permissions["can_invite_users"] is True
    assert principal.permissions["can_manage_roles"] is True
    # untouched flags remain False
    assert principal.permissions["can_create_release"] is False
    settings.RBAC_ENFORCEMENT_ENABLED = prev


@pytest.mark.asyncio
async def test_require_permissions_enforces_and_passes():
    principal = CurrentPrincipal(user=None, role_names=[], permissions={"a": True, "b": False})

    # missing permission -> 403
    checker = require_permissions("b")
    with pytest.raises(Exception) as ei:
        await checker(principal=principal)  # type: ignore[arg-type]
    assert getattr(ei.value, "status_code", None) == 403

    # grant permission -> passes and returns principal
    principal.permissions["b"] = True
    checker2 = require_permissions("a", "b")
    out = await checker2(principal=principal)  # type: ignore[arg-type]
    assert out is principal
