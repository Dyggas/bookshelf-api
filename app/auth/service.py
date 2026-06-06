from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.auth.password import hash_password, verify_password
from app.exceptions import AuthenticationError, ConflictError
from app.repositories.refresh_token_repo import RefreshTokenRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenResponse


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository()
        self.token_repo = RefreshTokenRepository()

    async def register(self, email: str, password: str) -> TokenResponse:
        existing = await self.user_repo.get_by_email(self.session, email)
        if existing:
            raise ConflictError("A user with this email already exists")

        user = await self.user_repo.create(self.session, email, hash_password(password))
        return await self._create_token_pair(user.id)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.user_repo.get_by_email(self.session, email)
        if not user or not verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        return await self._create_token_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        active = await self.token_repo.find_active_by_hash(self.session, refresh_token)

        if active:
            await self.token_repo.revoke(self.session, active.id)
            return await self._create_token_pair(active.user_id)

        # Token not found as active — check if it was already revoked (reuse)
        any_match = await self.token_repo.find_any_by_hash(self.session, refresh_token)
        if any_match:
            await self.token_repo.revoke_all_for_user(self.session, any_match.user_id)
            raise AuthenticationError("Token reuse detected. All sessions terminated.")

        raise AuthenticationError("Invalid or expired refresh token")

    async def logout(self, refresh_token: str) -> None:
        active = await self.token_repo.find_active_by_hash(self.session, refresh_token)
        if active:
            await self.token_repo.revoke(self.session, active.id)

    async def _create_token_pair(self, user_id) -> TokenResponse:
        access_token = create_access_token(str(user_id))

        refresh_value = RefreshTokenRepository.generate_token()
        await self.token_repo.create(self.session, user_id, refresh_value)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_value,
        )
