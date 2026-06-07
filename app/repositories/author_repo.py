from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.author import Author


class AuthorRepository:
    async def get_or_create(self, session: AsyncSession, name: str) -> Author:
        # Fast path: check if exists
        result = await session.execute(select(Author).where(Author.name == name))
        author = result.scalar_one_or_none()
        if author:
            return author

        # Insert with savepoint — handles race condition
        try:
            async with session.begin_nested():
                author = Author(name=name)
                session.add(author)
                await session.flush()
                return author
        except IntegrityError:
            # Savepoint rolled back — expire stale objects from identity map
            # so the subsequent select fetches fresh data from DB.
            session.expire_all()

        # Another request created it concurrently
        result = await session.execute(select(Author).where(Author.name == name))
        return result.scalar_one()
