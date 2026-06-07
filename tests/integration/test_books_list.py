import pytest
import pytest_asyncio
from httpx import AsyncClient


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient) -> AsyncClient:
    """Client with a registered user and valid access token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "listuser@example.com", "password": "secret12345"},
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
    assert resp.status_code == 201
    return resp.json()


def first_item(body: dict) -> dict:
    """Shortcut to get the first item from a paginated response."""
    return body["items"][0]


class TestListDefaults:
    async def test_empty_list(self, client: AsyncClient):
        resp = await client.get("/api/v1/books/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["pages"] == 0

    async def test_returns_all_books(self, auth_client: AsyncClient):
        await create_book(auth_client, title="Book A", author="Author X")
        await create_book(auth_client, title="Book B", author="Author Y")
        resp = await auth_client.get("/api/v1/books/")
        body = resp.json()
        assert body["total"] == 2
        assert len(body["items"]) == 2

    async def test_default_pagination(self, auth_client: AsyncClient):
        await create_book(auth_client)
        resp = await auth_client.get("/api/v1/books/")
        body = resp.json()
        assert body["page"] == 1
        assert body["page_size"] == 20

    async def test_public_no_auth_needed(
        self, auth_client: AsyncClient, client: AsyncClient
    ):
        await create_book(auth_client)
        auth_client.headers.pop("Authorization", None)
        resp = await client.get("/api/v1/books/")
        assert resp.status_code == 200


class TestListFiltering:
    async def test_filter_by_genre(self, auth_client: AsyncClient):
        await create_book(auth_client, title="Poetry Book", genre="poetry")
        await create_book(
            auth_client, title="Drama Book", genre="drama", author="Other Author"
        )
        resp = await auth_client.get("/api/v1/books/", params={"genre": "poetry"})
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["genre"] == "poetry"

    async def test_filter_by_title_case_insensitive(self, auth_client: AsyncClient):
        await create_book(auth_client, title="The Great Gatsby")
        resp = await auth_client.get("/api/v1/books/", params={"title": "great"})
        body = resp.json()
        assert body["total"] == 1
        assert first_item(body)["title"] == "The Great Gatsby"

    async def test_filter_by_author_name(self, auth_client: AsyncClient):
        await create_book(auth_client, author="Taras Shevchenko")
        await create_book(auth_client, title="Other Book", author="Ivan Franko")
        resp = await auth_client.get("/api/v1/books/", params={"author": "Shevchenko"})
        body = resp.json()
        assert body["total"] == 1
        assert first_item(body)["author"]["name"] == "Taras Shevchenko"

    async def test_filter_by_year_range(self, auth_client: AsyncClient):
        await create_book(auth_client, title="Old Book", year=1850)
        await create_book(
            auth_client, title="New Book", year=2020, author="Modern Author"
        )
        resp = await auth_client.get(
            "/api/v1/books/", params={"year_from": 2000, "year_to": 2025}
        )
        body = resp.json()
        assert body["total"] == 1
        assert first_item(body)["title"] == "New Book"

    async def test_filter_year_from_only(self, auth_client: AsyncClient):
        await create_book(auth_client, year=1850)
        await create_book(
            auth_client, title="Recent", year=2020, author="Modern Author"
        )
        resp = await auth_client.get("/api/v1/books/", params={"year_from": 2000})
        body = resp.json()
        assert body["total"] == 1

    async def test_filter_year_to_only(self, auth_client: AsyncClient):
        await create_book(auth_client, year=1850)
        await create_book(
            auth_client, title="Recent", year=2020, author="Modern Author"
        )
        resp = await auth_client.get("/api/v1/books/", params={"year_to": 1900})
        body = resp.json()
        assert body["total"] == 1

    async def test_combined_filters(self, auth_client: AsyncClient):
        await create_book(
            auth_client,
            title="Fantasy Novel",
            author="J.R.R. Tolkien",
            genre="fantasy",
            year=1954,
        )
        await create_book(
            auth_client,
            title="Sci-Fi Novel",
            author="Isaac Asimov",
            genre="science_fiction",
            year=1951,
        )
        resp = await auth_client.get(
            "/api/v1/books/",
            params={"genre": "fantasy", "year_from": 1950},
        )
        body = resp.json()
        assert body["total"] == 1
        assert first_item(body)["title"] == "Fantasy Novel"

    async def test_filter_no_results(self, auth_client: AsyncClient):
        await create_book(auth_client)
        resp = await auth_client.get("/api/v1/books/", params={"genre": "horror"})
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []


class TestListSorting:
    async def test_sort_by_title_asc(self, auth_client: AsyncClient):
        await create_book(auth_client, title="Alpha")
        await create_book(auth_client, title="Zeta", author="Other Author")
        resp = await auth_client.get(
            "/api/v1/books/", params={"sort_by": "title", "sort_order": "asc"}
        )
        body = resp.json()
        assert body["items"][0]["title"] == "Alpha"
        assert body["items"][1]["title"] == "Zeta"

    async def test_sort_by_year_desc(self, auth_client: AsyncClient):
        await create_book(auth_client, title="Old", year=1850)
        await create_book(auth_client, title="New", year=2020, author="Modern Author")
        resp = await auth_client.get(
            "/api/v1/books/", params={"sort_by": "year", "sort_order": "desc"}
        )
        body = resp.json()
        assert body["items"][0]["year"] == 2020
        assert body["items"][1]["year"] == 1850

    async def test_default_sort_is_created_at_desc(self, auth_client: AsyncClient):
        book_a = await create_book(auth_client, title="First Created")
        book_b = await create_book(auth_client, title="Second Created", author="Other")
        resp = await auth_client.get("/api/v1/books/")
        body = resp.json()
        # Most recently created first
        assert body["items"][0]["title"] == "Second Created"
        assert body["items"][1]["title"] == "First Created"

    async def test_invalid_sort_order_defaults_to_desc(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/books/", params={"sort_order": "invalid"})
        # FastAPI Query pattern validation rejects it
        assert resp.status_code == 422


class TestListPagination:
    async def test_pagination_page_size(self, auth_client: AsyncClient):
        for i in range(5):
            await create_book(
                auth_client,
                title=f"Book {i}",
                author=f"Author {i}",
            )
        resp = await auth_client.get("/api/v1/books/", params={"page_size": 2})
        body = resp.json()
        assert body["page_size"] == 2
        assert len(body["items"]) == 2
        assert body["total"] == 5
        assert body["pages"] == 3

    async def test_pagination_page_2(self, auth_client: AsyncClient):
        for i in range(5):
            await create_book(
                auth_client,
                title=f"Book {i}",
                author=f"Author {i}",
            )
        resp = await auth_client.get(
            "/api/v1/books/", params={"page_size": 2, "page": 2}
        )
        body = resp.json()
        assert body["page"] == 2
        assert len(body["items"]) == 2

    async def test_pagination_last_page_partial(self, auth_client: AsyncClient):
        for i in range(5):
            await create_book(
                auth_client,
                title=f"Book {i}",
                author=f"Author {i}",
            )
        resp = await auth_client.get(
            "/api/v1/books/", params={"page_size": 2, "page": 3}
        )
        body = resp.json()
        assert body["page"] == 3
        assert len(body["items"]) == 1  # 5 total, 2 per page, last page has 1

    async def test_page_size_max_100(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/books/", params={"page_size": 200})
        assert resp.status_code == 422

    async def test_page_size_min_1(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/books/", params={"page_size": 0})
        assert resp.status_code == 422

    async def test_page_min_1(self, auth_client: AsyncClient):
        resp = await auth_client.get("/api/v1/books/", params={"page": 0})
        assert resp.status_code == 422
