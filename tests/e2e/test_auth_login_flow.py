import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.rbac import TokenPair
from app.core.security import create_refresh_token
from app.routers import auth as auth_router


class _FakeAuthServiceNone:
    async def authenticate(self, username: str, password: str):
        return None


class _FakeAuthServiceSuccess:
    async def authenticate(self, username: str, password: str):
        return TokenPair(access_token="a", refresh_token="r")


@pytest.mark.asyncio
async def test_login_missing_fields_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/login", json={})
    assert resp.status_code == 422
    data = resp.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401():
    app.dependency_overrides[auth_router.get_auth_service] = lambda: _FakeAuthServiceNone()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/auth/login", json={"username": "u", "password": "p"})
        assert resp.status_code == 401
        body = resp.json()
        assert body["error"]["code"] == "UNAUTHORIZED"
    finally:
        app.dependency_overrides.pop(auth_router.get_auth_service, None)


@pytest.mark.asyncio
async def test_login_success_returns_tokenpair():
    app.dependency_overrides[auth_router.get_auth_service] = lambda: _FakeAuthServiceSuccess()
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/auth/login", json={"username": "admin", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert set(data.keys()) == {"access_token", "refresh_token", "token_type"}
        assert data["token_type"] == "bearer"
    finally:
        app.dependency_overrides.pop(auth_router.get_auth_service, None)


@pytest.mark.asyncio
async def test_refresh_missing_header_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/refresh", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_valid_refresh_token_returns_tokens():
    token = create_refresh_token("user-123")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"access_token", "refresh_token", "token_type"}


@pytest.mark.asyncio
async def test_register_disabled_returns_403(monkeypatch):
    # Disable registration
    from app.core import config as config_module

    monkeypatch.setattr(config_module.settings, "ADMIN_REGISTRATION_ENABLED", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "username": "jdoe",
            "full_name": "Jane Doe",
            "email": "jdoe@example.com",
            "password": "StrongP@ssw0rd",
            "role_ids": [],
        }
        resp = await ac.post("/auth/register", json=payload)
    assert resp.status_code == 403
    body = resp.json()
    assert body["error"]["code"] == "FORBIDDEN"
