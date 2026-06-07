import csv
import io
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.book import (
    BookCreate,
    BookExportRow,
    BookFilters,
    BookResponse,
    BookUpdate,
    BulkImportResult,
    PaginatedResponse,
)
from app.services.book_service import BookService

router = APIRouter(prefix="/api/v1/books", tags=["books"])


def _parse_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


@router.get("/", response_model=PaginatedResponse)
async def list_books(
    filters: BookFilters = Depends(),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
):
    service = BookService(session)
    return await service.list_books(filters, page, page_size, sort_by, sort_order)


@router.post("/", response_model=BookResponse, status_code=201)
async def create_book(
    body: BookCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = BookService(session)
    book = await service.create_book(body)
    await session.commit()
    return book


@router.post("/import", response_model=BulkImportResult)
async def import_books(
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    content_type = request.headers.get("content-type", "")
    body = await request.body()

    if "csv" in content_type:
        books_data = _parse_csv(body.decode("utf-8"))
    else:
        books_data = json.loads(body)

    # Validate all rows
    try:
        validated = [BookCreate(**row) for row in books_data]
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=json.loads(e.json())) from e

    service = BookService(session)
    result = await service.bulk_import(validated)
    await session.commit()
    return result


@router.get("/export", response_model=list[BookExportRow])
async def export_books(
    session: AsyncSession = Depends(get_session),
):
    service = BookService(session)
    return await service.export_books()


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    service = BookService(session)
    return await service.get_book(book_id)


@router.patch("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: UUID,
    body: BookUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = BookService(session)
    book = await service.update_book(book_id, body)
    await session.commit()
    return book


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    service = BookService(session)
    await service.delete_book(book_id)
    await session.commit()
