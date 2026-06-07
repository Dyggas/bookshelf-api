import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """Client with a registered user and valid access token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "bookuser@example.com", "password": "secret12345"},
    )
    tokens = resp.json()
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return client


async def create_book(client: AsyncClient, **overrides) -> dict:
    """Helper to create a book with sensible defaults."""
    data = {
        "title": "Kobzar",
        "author": "Taras Shevchenko",
        "genre": "poetry",
        "year": 1840,
    }
    data.update(overrides)
    resp = await client.post("/api/v1/books/", json=data)
    return resp.json(), resp.status_code


class TestCreateBook:
    async def test_create_success(self, auth_client: AsyncClient):
        data, status = await create_book(auth_client)
        assert status == 201
        assert data["title"] == "Kobzar"
        assert data["author"]["name"] == "Taras Shevchenko"
        assert data["genre"] == "poetry"
        assert data["year"] == 1840
        assert "id" in data
        assert "created_at" in data

    async def test_create_reuses_existing_author(self, auth_client: AsyncClient):
        await create_book(auth_client, title="Book One")
        data, status = await create_book(auth_client, title="Book Two")
        assert status == 201
        assert data["author"]["name"] == "Taras Shevchenko"

    async def test_create_duplicate_title_author(self, auth_client: AsyncClient):
        await create_book(auth_client)
        _, status = await create_book(auth_client)
        assert status == 409

    async def test_create_unauthenticated(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/books/",
            json={
                "title": "Kobzar",
                "author": "Taras Shevchenko",
                "genre": "poetry",
                "year": 1840,
            },
        )
        assert resp.status_code == 401

    async def test_create_invalid_genre(self, auth_client: AsyncClient):
        _, status = await create_book(auth_client, genre="cooking")
        assert status == 422

    async def test_create_year_out_of_range(self, auth_client: AsyncClient):
        _, status = await create_book(auth_client, year=1799)
        assert status == 422


class TestGetBook:
    async def test_get_success(self, auth_client: AsyncClient):
        book, _ = await create_book(auth_client)
        resp = await auth_client.get(f"/api/v1/books/{book['id']}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Kobzar"
        assert resp.json()["author"]["name"] == "Taras Shevchenko"

    async def test_get_public_no_auth_needed(
        self, client: AsyncClient, auth_client: AsyncClient
    ):
        book, _ = await create_book(auth_client)
        # Remove auth header to verify public access
        auth_client.headers.pop("Authorization", None)
        resp = await client.get(f"/api/v1/books/{book['id']}")
        assert resp.status_code == 200

    async def test_get_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.get(
            "/api/v1/books/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404


class TestUpdateBook:
    async def test_partial_update_title(self, auth_client: AsyncClient):
        book, _ = await create_book(auth_client)
        resp = await auth_client.patch(
            f"/api/v1/books/{book['id']}", json={"title": "Updated Title"}
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"
        assert resp.json()["author"]["name"] == "Taras Shevchenko"  # unchanged

    async def test_update_genre(self, auth_client: AsyncClient):
        book, _ = await create_book(auth_client)
        resp = await auth_client.patch(
            f"/api/v1/books/{book['id']}", json={"genre": "drama"}
        )
        assert resp.status_code == 200
        assert resp.json()["genre"] == "drama"

    async def test_update_year(self, auth_client: AsyncClient):
        book, _ = await create_book(auth_client)
        resp = await auth_client.patch(
            f"/api/v1/books/{book['id']}", json={"year": 1860}
        )
        assert resp.status_code == 200
        assert resp.json()["year"] == 1860

    async def test_update_author(self, auth_client: AsyncClient):
        book, _ = await create_book(auth_client)
        resp = await auth_client.patch(
            f"/api/v1/books/{book['id']}", json={"author": "Ivan Franko"}
        )
        assert resp.status_code == 200
        assert resp.json()["author"]["name"] == "Ivan Franko"

    async def test_update_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.patch(
            "/api/v1/books/00000000-0000-0000-0000-000000000000",
            json={"title": "Nope"},
        )
        assert resp.status_code == 404

    async def test_update_unauthenticated(
        self, client: AsyncClient, auth_client: AsyncClient
    ):
        book, _ = await create_book(auth_client)
        # auth_client added header to shared client — remove it
        client.headers.pop("Authorization", None)
        resp = await client.patch(
            f"/api/v1/books/{book['id']}", json={"title": "Hacked"}
        )
        assert resp.status_code == 401

    async def test_empty_update_returns_book(self, auth_client: AsyncClient):
        book, _ = await create_book(auth_client)
        resp = await auth_client.patch(f"/api/v1/books/{book['id']}", json={})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Kobzar"


class TestDeleteBook:
    async def test_delete_success(self, auth_client: AsyncClient):
        book, _ = await create_book(auth_client)
        resp = await auth_client.delete(f"/api/v1/books/{book['id']}")
        assert resp.status_code == 204

        # Verify it's gone
        resp = await auth_client.get(f"/api/v1/books/{book['id']}")
        assert resp.status_code == 404

    async def test_delete_nonexistent(self, auth_client: AsyncClient):
        resp = await auth_client.delete(
            "/api/v1/books/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404

    async def test_delete_unauthenticated(
        self, client: AsyncClient, auth_client: AsyncClient
    ):
        book, _ = await create_book(auth_client)
        client.headers.pop("Authorization", None)
        resp = await client.delete(f"/api/v1/books/{book['id']}")
        assert resp.status_code == 401


class TestFullLifecycle:
    async def test_create_read_update_delete(self, auth_client: AsyncClient):
        # Create
        book, status = await create_book(auth_client)
        assert status == 201

        # Read
        resp = await auth_client.get(f"/api/v1/books/{book['id']}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Kobzar"

        # Update
        resp = await auth_client.patch(
            f"/api/v1/books/{book['id']}",
            json={"title": "Kobzar (2nd Edition)", "year": 1860},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Kobzar (2nd Edition)"
        assert resp.json()["year"] == 1860

        # Delete
        resp = await auth_client.delete(f"/api/v1/books/{book['id']}")
        assert resp.status_code == 204

        # Confirm gone
        resp = await auth_client.get(f"/api/v1/books/{book['id']}")
        assert resp.status_code == 404
