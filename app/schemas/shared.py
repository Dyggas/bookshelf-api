from pydantic import BaseModel


class BulkImportError(BaseModel):
    row: int
    data: dict
    reason: str


class BulkImportResult(BaseModel):
    total: int
    imported: int
    failed: int
    errors: list[BulkImportError]


class ErrorResponse(BaseModel):
    detail: str
    status: int
