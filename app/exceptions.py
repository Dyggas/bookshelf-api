from fastapi import HTTPException


class AppError(HTTPException):
    """Base application error with structured detail."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(AppError):
    def __init__(self, resource: str, id: str):
        super().__init__(status_code=404, detail=f"{resource} with id '{id}' not found")


class ConflictError(AppError):
    def __init__(self, detail: str):
        super().__init__(status_code=409, detail=detail)


class AuthenticationError(AppError):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(status_code=401, detail=detail)


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=403, detail=detail)


class BadRequestError(AppError):
    def __init__(self, detail: str):
        super().__init__(status_code=400, detail=detail)
