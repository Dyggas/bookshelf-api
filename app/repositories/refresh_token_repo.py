import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.refresh_token import RefreshToken


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenRepository:
    async def create(
        self, session: AsyncSession, user_id: UUID, token: str
    ) -> RefreshToken:
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=_hash_token(token),
            expires_at=expires_at,
        )
        session.add(refresh_token)
        await session.flush()
        return refresh_token

    async def find_active_by_hash(
        self, session: AsyncSession, token: str
    ) -> RefreshToken | None:
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == _hash_token(token),
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one_or_none()

    async def find_any_by_hash(
        self, session: AsyncSession, token: str
    ) -> RefreshToken | None:
        result = await session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == _hash_token(token),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, session: AsyncSession, token_id: UUID) -> None:
        await session.execute(
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await session.flush()

    async def revoke_all_for_user(self, session: AsyncSession, user_id: UUID) -> None:
        await session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await session.flush()

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(64)
