from fastapi import FastAPI

app = FastAPI(
    title="Bookshelf API",
    description="Book Management System",
    version="0.1.0",
)


@app.get("/")
async def root():
    return {"message": "Bookshelf API", "docs": "/docs"}
