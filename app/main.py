from fastapi import FastAPI

from app.config import settings
from app.error_handlers import register_error_handlers
from app.logging_config import setup_logging
from app.middleware import RequestIDMiddleware
from app.routers.auth import router as auth_router
from app.routers.books import router as books_router
from app.routers.health import router as health_router

setup_logging(debug=settings.DEBUG)

app = FastAPI(
    title="Bookshelf API",
    description="Book Management System",
    version="0.1.0",
)

app.add_middleware(RequestIDMiddleware)
register_error_handlers(app)
app.include_router(auth_router)
app.include_router(books_router)
app.include_router(health_router)


@app.get("/")
async def root():
    return {"message": "Bookshelf API", "docs": "/docs"}
