from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.database import get_session
from app.exceptions import AuthenticationError
from app.models.user import User
from app.repositories.user_repo import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise AuthenticationError()
        user_id = UUID(payload.get("sub"))
    except (jwt.PyJWTError, ValueError):
        raise AuthenticationError()

    user = await UserRepository().get_by_id(session, user_id)
    if user is None:
        raise AuthenticationError()

    return user
