from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    async def get_by_id(self, session: AsyncSession, id: UUID) -> User | None:
        return await session.get(User, id)

    async def get_by_email(self, session: AsyncSession, email: str) -> User | None:
        result = await session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create(
        self, session: AsyncSession, email: str, password_hash: str
    ) -> User:
        user = User(email=email, password_hash=password_hash)
        session.add(user)
        await session.flush()
        return user
