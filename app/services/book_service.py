import math
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.exceptions import ConflictError, NotFoundError
from app.models.author import Author
from app.models.book import Book
from app.repositories.author_repo import AuthorRepository
from app.repositories.book_repo import BookRepository
from app.schemas.book import (
    BookCreate,
    BookExportRow,
    BookFilters,
    BookUpdate,
    BulkImportResult,
    PaginatedResponse,
)


class BookService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.book_repo = BookRepository()
        self.author_repo = AuthorRepository()

    async def _load_book(self, book_id: UUID) -> Book:
        """Load a book with author, or raise 404."""
        result = await self.session.execute(
            select(Book)
            .where(Book.id == book_id)
            .options(selectinload(Book.author))
            .execution_options(populate_existing=True)
        )
        book = result.scalar_one_or_none()
        if not book:
            raise NotFoundError("Book", str(book_id))
        return book

    async def create_book(self, data: BookCreate) -> Book:
        author = await self.author_repo.get_or_create(self.session, data.author)

        try:
            async with self.session.begin_nested():
                book = await self.book_repo.create(
                    self.session,
                    title=data.title,
                    author_id=author.id,
                    genre=data.genre.value,
                    year=data.year,
                )
        except IntegrityError:
            raise ConflictError("This book already exists for this author")

        return await self._load_book(book.id)

    async def get_book(self, book_id: UUID) -> Book:
        return await self._load_book(book_id)

    async def update_book(self, book_id: UUID, data: BookUpdate) -> Book:
        book = await self._load_book(book_id)

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            return book

        if "author" in update_data:
            author = await self.author_repo.get_or_create(
                self.session, update_data.pop("author")
            )
            update_data["author_id"] = author.id

        if "genre" in update_data and update_data["genre"] is not None:
            update_data["genre"] = update_data["genre"].value

        for key, value in update_data.items():
            setattr(book, key, value)

        try:
            async with self.session.begin_nested():
                await self.session.flush()
        except IntegrityError:
            raise ConflictError("This book already exists for this author")

        # Fetch fresh from DB with author loaded
        return await self._load_book(book.id)

    async def delete_book(self, book_id: UUID) -> None:
        book = await self._load_book(book_id)
        await self.book_repo.delete(self.session, book)

    async def list_books(
        self,
        filters: BookFilters,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> PaginatedResponse:
        query = select(Book).options(selectinload(Book.author))
        count_query = select(func.count()).select_from(Book)

        # Apply filters
        if filters.title:
            query = query.where(Book.title.ilike(f"%{filters.title}%"))
            count_query = count_query.where(Book.title.ilike(f"%{filters.title}%"))
        if filters.author:
            query = query.join(Book.author).where(
                Author.name.ilike(f"%{filters.author}%")
            )
            count_query = count_query.join(Book.author).where(
                Author.name.ilike(f"%{filters.author}%")
            )
        if filters.genre:
            query = query.where(Book.genre == filters.genre.value)
            count_query = count_query.where(Book.genre == filters.genre.value)
        if filters.year_from is not None:
            query = query.where(Book.year >= filters.year_from)
            count_query = count_query.where(Book.year >= filters.year_from)
        if filters.year_to is not None:
            query = query.where(Book.year <= filters.year_to)
            count_query = count_query.where(Book.year <= filters.year_to)

        # Total count
        total = (await self.session.execute(count_query)).scalar_one()

        # Sorting
        allowed_sort = {
            "title": Book.title,
            "year": Book.year,
            "genre": Book.genre,
            "created_at": Book.created_at,
        }
        sort_col = allowed_sort.get(sort_by, Book.created_at)
        if sort_order == "asc":
            query = query.order_by(sort_col.asc(), Book.title.asc())
        else:
            query = query.order_by(sort_col.desc(), Book.title.asc())

        # Pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        result = await self.session.execute(query)
        books = list(result.scalars().all())

        return PaginatedResponse(
            items=books,
            total=total,
            page=page,
            page_size=page_size,
            pages=math.ceil(total / page_size) if total > 0 else 0,
        )

    async def bulk_import(self, books_data: list[BookCreate]) -> BulkImportResult:
        total = len(books_data)
        if total == 0:
            return BulkImportResult(total=0, created=0, skipped=0)

        # 1. Collect all unique author names
        author_names = list({book_data.author for book_data in books_data})

        # 2. Resolve authors: insert new ones, then select all to get IDs
        await self.session.execute(
            pg_insert(Author)
            .values([{"name": name} for name in author_names])
            .on_conflict_do_nothing(index_elements=["name"])
        )
        await self.session.flush()

        result = await self.session.execute(
            select(Author).where(Author.name.in_(author_names))
        )
        author_map = {a.name: a.id for a in result.scalars().all()}

        # 3. Build book row dicts with resolved author_id
        book_rows = []
        for book_data in books_data:
            book_rows.append(
                {
                    "title": book_data.title,
                    "author_id": author_map[book_data.author],
                    "genre": book_data.genre.value,
                    "year": book_data.year,
                }
            )

        # 4. Insert books in batches, skipping duplicates
        batch_size = 100
        created = 0
        for i in range(0, len(book_rows), batch_size):
            batch = book_rows[i : i + batch_size]
            result = await self.session.execute(
                pg_insert(Book)
                .values(batch)
                .on_conflict_do_nothing(constraint="uq_books_title_author")
            )
            created += result.rowcount

        await self.session.flush()

        return BulkImportResult(
            total=total,
            created=created,
            skipped=total - created,
        )

    async def export_books(self) -> list[BookExportRow]:
        result = await self.session.execute(
            select(Book).options(selectinload(Book.author))
        )
        books = list(result.scalars().all())
        return [
            BookExportRow(
                id=book.id,
                title=book.title,
                author=book.author.name,
                genre=book.genre,
                year=book.year,
                created_at=book.created_at,
                updated_at=book.updated_at,
            )
            for book in books
        ]
