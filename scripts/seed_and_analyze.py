"""
Seed the database with books and analyze query plans.

Usage:
    docker compose exec api python scripts/seed_and_analyze.py
"""

import asyncio
import random
import time

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.database import async_session_factory
from app.enums import Genre
from app.models.author import Author
from app.models.book import Book

GENRES = [g.value for g in Genre]
AUTHOR_NAMES = [f"Author {i}" for i in range(2000)]
BOOKS_COUNT = 1_000_000
BATCH_SIZE = 5000


async def seed():
    async with async_session_factory() as session:
        count = (
            await session.execute(select(func.count()).select_from(Book))
        ).scalar_one()
        if count >= BOOKS_COUNT:
            print(f"Already have {count} books, skipping seed.")
            return

        print(f"Seeding {BOOKS_COUNT} books...")

        print("  Inserting authors...")
        await session.execute(
            pg_insert(Author)
            .values([{"name": name} for name in AUTHOR_NAMES])
            .on_conflict_do_nothing(index_elements=["name"])
        )
        await session.flush()

        result = await session.execute(select(Author.id))
        author_ids = [row[0] for row in result.all()]
        print(f"  {len(author_ids)} authors available.")

        print("  Inserting books...")
        inserted = 0
        start = time.perf_counter()
        for i in range(0, BOOKS_COUNT, BATCH_SIZE):
            batch = []
            for j in range(min(BATCH_SIZE, BOOKS_COUNT - i)):
                batch.append(
                    {
                        "title": f"Book {i + j}",
                        "author_id": random.choice(author_ids),
                        "genre": random.choice(GENRES),
                        "year": random.randint(1800, 2025),
                    }
                )
            result = await session.execute(
                pg_insert(Book)
                .values(batch)
                .on_conflict_do_nothing(constraint="uq_books_title_author")
            )
            inserted += result.rowcount

        await session.commit()
        elapsed = time.perf_counter() - start
        print(f"  Inserted {inserted} books in {elapsed:.1f}s")


async def analyze():
    async with async_session_factory() as session:
        print("\n" + "=" * 60)
        total = (
            await session.execute(select(func.count()).select_from(Book))
        ).scalar_one()
        print(f"QUERY PLAN ANALYSIS ({total:,} books)")
        print("=" * 60)

        queries = {
            "Unfiltered (default pagination)": (
                "EXPLAIN ANALYZE "
                "SELECT b.* FROM books b "
                "ORDER BY b.created_at DESC, b.title ASC "
                "LIMIT 20 OFFSET 0"
            ),
            "Filter by genre (no index)": (
                "EXPLAIN ANALYZE "
                "SELECT b.* FROM books b "
                "WHERE b.genre = 'fiction' "
                "ORDER BY b.created_at DESC, b.title ASC "
                "LIMIT 20 OFFSET 0"
            ),
            "Filter by year range (ix_books_year)": (
                "EXPLAIN ANALYZE "
                "SELECT b.* FROM books b "
                "WHERE b.year >= 2000 AND b.year <= 2025 "
                "ORDER BY b.created_at DESC, b.title ASC "
                "LIMIT 20 OFFSET 0"
            ),
            "Filter by author name (ix_books_author_id on books)": (
                "EXPLAIN ANALYZE "
                "SELECT b.* FROM books b "
                "JOIN authors a ON b.author_id = a.id "
                "WHERE a.name ILIKE '%%Author 1%%' "
                "ORDER BY b.created_at DESC, b.title ASC "
                "LIMIT 20 OFFSET 0"
            ),
            "Filter by title ILIKE (no index)": (
                "EXPLAIN ANALYZE "
                "SELECT b.* FROM books b "
                "WHERE b.title ILIKE '%%Book 999%%' "
                "ORDER BY b.created_at DESC, b.title ASC "
                "LIMIT 20 OFFSET 0"
            ),
            "Count all": (
                "EXPLAIN ANALYZE SELECT COUNT(*) FROM books"
            ),
            "Count filtered by genre (no index)": (
                "EXPLAIN ANALYZE SELECT COUNT(*) FROM books WHERE genre = 'fiction'"
            ),
            "Deep pagination — OFFSET 1980 (no index)": (
                "EXPLAIN ANALYZE "
                "SELECT b.* FROM books b "
                "ORDER BY b.created_at DESC, b.title ASC "
                "LIMIT 20 OFFSET 1980"
            ),
        }

        for label, sql in queries.items():
            print(f"\n--- {label} ---")
            result = await session.execute(text(sql))
            for row in result:
                print(f"  {row[0]}")


async def main():
    await seed()
    await analyze()


if __name__ == "__main__":
    asyncio.run(main())
