import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.enums import Genre
from app.schemas.author import AuthorBrief

CURRENT_YEAR = datetime.now().year


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    author: str = Field(min_length=1, max_length=255)

    @field_validator("title", "author")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()

    genre: Genre
    year: int = Field(ge=1800, le=CURRENT_YEAR)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    genre: Genre | None = None
    year: int | None = Field(default=None, ge=1800, le=CURRENT_YEAR)


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
    year_to: int | None = Field(default=None, le=CURRENT_YEAR)


class PaginatedResponse(BaseModel):
    items: list[BookResponse]
    total: int
    page: int
    page_size: int
    pages: int


class BulkImportResult(BaseModel):
    total: int  # how many rows were in the file
    created: int  # how many were actually inserted
    skipped: int  # how many were duplicates (total - created)


class BookExportRow(BaseModel):
    id: uuid.UUID
    title: str
    author: str  # just the author name for export
    genre: Genre
    year: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
