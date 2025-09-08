import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.rbac import User
from app.utils.time import utcnow


class _FakeAuthService:
    async def register_user(self, payload):  # noqa: ARG002
        return User(
            _id="u1",
            username="jdoe",
            full_name="Jane Doe",
            email="jdoe@example.com",
            password_hash="h",
            role_ids=[],
            assigned_squad_ids=[],
            created_at=utcnow(),
        )


@pytest.mark.asyncio
async def test_register_success(monkeypatch):
    # Enable registration and override service
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "ADMIN_REGISTRATION_ENABLED", True)

    from app.routers import auth as auth_router
    app.dependency_overrides[auth_router.get_auth_service] = lambda: _FakeAuthService()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {
            "username": "jdoe",
            "full_name": "Jane Doe",
            "email": "jdoe@example.com",
            "password": "secret",
            "role_ids": [],
        }
        resp = await ac.post("/auth/register", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "jdoe"

    app.dependency_overrides.pop(auth_router.get_auth_service, None)
