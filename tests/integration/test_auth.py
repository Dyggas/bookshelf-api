import pytest
from httpx import AsyncClient


@pytest.fixture
async def registered_client(client: AsyncClient) -> dict:
    """Register a user and return tokens + credentials."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "secret12345"},
    )
    assert resp.status_code == 201
    return resp.json()


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "secret12345"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_register_duplicate_email(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "dup@example.com", "password": "secret12345"},
        )
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "dup@example.com", "password": "otherpass1"},
        )
        assert resp.status_code == 409
        assert "already exists" in resp.json()["detail"]

    async def test_register_invalid_email(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "not-an-email", "password": "secret12345"},
        )
        assert resp.status_code == 422

    async def test_register_short_password(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "user@example.com", "password": "short"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "login@example.com", "password": "secret12345"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "secret12345"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient):
        await client.post(
            "/api/v1/auth/register",
            json={"email": "wrong@example.com", "password": "secret12345"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "wrong@example.com", "password": "badpassword"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@example.com", "password": "secret12345"},
        )
        assert resp.status_code == 401


class TestRefresh:
    async def test_refresh_success(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": "refresh@example.com", "password": "secret12345"},
        )
        tokens = reg.json()

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["access_token"] != tokens["access_token"]
        assert data["refresh_token"] != tokens["refresh_token"]

    async def test_refresh_gives_new_pair(self, client: AsyncClient):
        """Old refresh token should not work after rotation."""
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": "rotate@example.com", "password": "secret12345"},
        )
        tokens = reg.json()

        # First refresh succeeds
        await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )

        # Same token again — reuse detected
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 401
        assert "reuse" in resp.json()["detail"].lower()

    async def test_refresh_invalid_token(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "totally-fake-token"},
        )
        assert resp.status_code == 401


class TestLogout:
    async def test_logout_success(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": "logout@example.com", "password": "secret12345"},
        )
        tokens = reg.json()

        resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 204

    async def test_logout_invalidates_refresh(self, client: AsyncClient):
        reg = await client.post(
            "/api/v1/auth/register",
            json={"email": "logout2@example.com", "password": "secret12345"},
        )
        tokens = reg.json()

        await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
        )

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert resp.status_code == 401
