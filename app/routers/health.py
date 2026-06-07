from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    # Verify database connectivity
    await session.execute(text("SELECT 1"))
    return {"status": "healthy", "database": "connected"}
