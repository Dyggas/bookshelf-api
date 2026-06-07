from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.schemas.book import BookFilters


class BookRepository:
    async def get_by_id(self, session: AsyncSession, book_id: UUID) -> Book | None:
        result = await session.execute(select(Book).where(Book.id == book_id))
        return result.scalar_one_or_none()

    async def create(
        self, session: AsyncSession, title: str, author_id: UUID, genre: str, year: int
    ) -> Book:
        book = Book(title=title, author_id=author_id, genre=genre, year=year)
        session.add(book)
        await session.flush()
        return book

    async def delete(self, session: AsyncSession, book: Book) -> None:
        await session.delete(book)
        await session.flush()
