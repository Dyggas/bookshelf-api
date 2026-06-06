import asyncio
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.database import get_session
from app.main import app
from app.models import Author, Book, RefreshToken, User  # noqa: F401
from app.models.base import Base

TEST_DATABASE_URL = settings.DATABASE_URL.replace("/bookshelf", "/bookshelf_test")
ADMIN_DATABASE_URL = settings.DATABASE_URL.replace("/bookshelf", "/postgres")


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Create test database and tables once per test session."""
    admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.begin() as conn:
        await conn.execute(text("DROP DATABASE IF EXISTS bookshelf_test"))
        await conn.execute(text("CREATE DATABASE bookshelf_test"))
    await admin_engine.dispose()

    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    yield

    admin_engine = create_async_engine(ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.begin() as conn:
        await conn.execute(text("DROP DATABASE IF EXISTS bookshelf_test"))
    await admin_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Transactional session — rolls back after each test for isolation."""
    engine = create_async_engine(TEST_DATABASE_URL)
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    yield session

    await session.close()
    await transaction.rollback()
    await connection.close()
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Async test client with the test database session injected."""

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
