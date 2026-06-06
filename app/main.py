from fastapi import FastAPI

from app.error_handlers import register_error_handlers
from app.routers.auth import router as auth_router

app = FastAPI(
    title="Bookshelf API",
    description="Book Management System",
    version="0.1.0",
)

register_error_handlers(app)
app.include_router(auth_router)


@app.get("/")
async def root():
    return {"message": "Bookshelf API", "docs": "/docs"}
