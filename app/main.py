from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.documents import router as documents_router

app = FastAPI(
    title="Document Intelligence API",
    description="An AI-powered document processing and search platform.",
    version="1.0.0"
)

app.include_router(documents_router)

@app.get("/")
def root():
    return {
        "message": "Document Intelligence API is running"
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "status": "healthy",
        "database": "connected"
    }