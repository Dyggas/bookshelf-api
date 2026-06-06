import uuid
from datetime import datetime
from typing import Literal

from app.schemas.author import AuthorBrief
from pydantic import BaseModel, Field

from app.enums import Genre


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=255)
    genre: Genre
    year: int = Field(ge=1800, le=2026)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    genre: Genre | None = None
    year: int | None = Field(default=None, ge=1800, le=2026)


class BookResponse(BaseModel):
    id: uuid.UUID
    title: str
    author: AuthorBrief
    genre: Genre
    year: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookFilters(BaseModel):
    title: str | None = None
    author: str | None = None
    genre: Genre | None = None
    year_from: int | None = Field(default=None, ge=1800)
    year_to: int | None = Field(default=None, le=2026)


class PaginatedResponse(BaseModel):
    items: list[BookResponse]
    total: int
    page: int
    page_size: int
    pages: int
