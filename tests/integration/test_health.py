import pytest_asyncio
from httpx import AsyncClient


class TestHealth:
    async def test_health_returns_200(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["database"] == "connected"

    async def test_health_public_no_auth(self, client: AsyncClient):
        # No Authorization header needed
        resp = await client.get("/health")
        assert resp.status_code == 200
