import pytest
import pytest_asyncio
from httpx import AsyncClient

IMPORT_URL = "/api/v1/books/import"
EXPORT_URL = "/api/v1/books/export"
CREATE_URL = "/api/v1/books/"


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "bulkuser@example.com", "password": "secret12345"},
    )
    tokens = resp.json()
    client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return client


BOOKS = [
    {
        "title": "Kobzar",
        "author": "Taras Shevchenko",
        "genre": "poetry",
        "year": 1840
    },
    {
        "title": "1984",
        "author": "George Orwell",
        "genre": "science_fiction",
        "year": 1949
    },
    {
        "title": "The Shining",
        "author": "Stephen King",
        "genre": "horror",
        "year": 1977
    },
]


class TestImport:
    async def test_import_json_success(self, auth_client: AsyncClient):
        resp = await auth_client.post(IMPORT_URL, json=BOOKS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["created"] == 3
        assert body["skipped"] == 0

    async def test_import_csv_success(self, auth_client: AsyncClient):
        csv_text = (
            "title,author,genre,year\n"
            "Dune,Frank Herbert,science_fiction,1965\n"
            "Emma,Jane Austen,romance,1815\n"
        )
        csv_bytes = csv_text.encode("utf-8")
        resp = await auth_client.post(
            IMPORT_URL,
            content=csv_bytes,
            headers={"Content-Type": "text/csv"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["created"] == 2
        assert body["skipped"] == 0

    async def test_import_skips_duplicates(self, auth_client: AsyncClient):
        # First import
        resp = await auth_client.post(IMPORT_URL, json=BOOKS)
        assert resp.status_code == 200
        assert resp.json()["created"] == 3

        # Second import — same books
        resp = await auth_client.post(IMPORT_URL, json=BOOKS)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["created"] == 0
        assert body["skipped"] == 3

    async def test_import_mixed_valid_and_duplicates(self, auth_client: AsyncClient):
        # First batch: 3 books
        await auth_client.post(IMPORT_URL, json=BOOKS)

        # Second batch: 2 duplicates + 1 new
        second_batch = [
            BOOKS[0],  # duplicate
            BOOKS[1],  # duplicate
            {
                "title": "Pride and Prejudice",
                "author": "Jane Austen",
                "genre": "romance",
                "year": 1813,
            },
        ]
        resp = await auth_client.post(IMPORT_URL, json=second_batch)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 3
        assert body["created"] == 1
        assert body["skipped"] == 2

    async def test_import_invalid_genre(self, auth_client: AsyncClient):
        bad_books = [
            {
                "title": "Bad Book",
                "author": "Nobody",
                "genre": "cooking",
                "year": 2020,
            },
        ]
        resp = await auth_client.post(IMPORT_URL, json=bad_books)
        assert resp.status_code == 422

    async def test_import_empty_list(self, auth_client: AsyncClient):
        resp = await auth_client.post(IMPORT_URL, json=[])
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["created"] == 0
        assert body["skipped"] == 0

    async def test_import_requires_auth(self, client: AsyncClient):
        client.headers.pop("Authorization", None)
        resp = await client.post(IMPORT_URL, json=BOOKS)
        assert resp.status_code == 401


class TestExport:
    async def test_export_empty(self, client: AsyncClient):
        resp = await client.get(EXPORT_URL)
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_export_returns_books(self, auth_client: AsyncClient):
        # Create 2 books via the standard endpoint
        for book in BOOKS[:2]:
            resp = await auth_client.post(CREATE_URL, json=book)
            assert resp.status_code == 201

        # Export
        resp = await auth_client.get(EXPORT_URL)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

        for item in data:
            assert "id" in item
            assert "title" in item
            assert "author" in item
            assert isinstance(item["author"], str)
            assert "genre" in item
            assert "year" in item
            assert "created_at" in item
            assert "updated_at" in item

        titles = {b["title"] for b in data}
        assert titles == {"Kobzar", "1984"}

    async def test_export_public_no_auth(
        self, client: AsyncClient, auth_client: AsyncClient
    ):
        # Create a book via authenticated client
        resp = await auth_client.post(CREATE_URL, json=BOOKS[0])
        assert resp.status_code == 201

        # Export without auth (client fixture has no auth header)
        client.headers.pop("Authorization", None)
        resp = await client.get(EXPORT_URL)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
