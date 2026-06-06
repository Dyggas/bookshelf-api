from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.service import AuthService
from app.database import get_session
from app.schemas.auth import RefreshRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    tokens = await service.register(body.email, body.password)
    await session.commit()
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    tokens = await service.login(form.username, form.password)
    await session.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    tokens = await service.refresh(body.refresh_token)
    await session.commit()
    return tokens


@router.post("/logout", status_code=204)
async def logout(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    service = AuthService(session)
    await service.logout(body.refresh_token)
    await session.commit()
