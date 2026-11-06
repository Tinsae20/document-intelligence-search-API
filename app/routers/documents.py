
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Document

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = Path("data/uploads")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported.",
        )

    # Read one byte beyond the limit to detect oversized uploads.
    file_content = await file.read(MAX_FILE_SIZE + 1)

    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size exceeds the 10 MB limit.",
        )

    # Validate the actual file content, not just its extension.
    if extension == ".pdf":
        if not file_content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is not a valid PDF.",
            )

    elif extension == ".txt":
        try:
            file_content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="TXT files must use UTF-8 encoding.",
            )

    # Generate a unique filename to prevent collisions.
    stored_filename = f"{uuid.uuid4().hex}{extension}"

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / stored_filename

    try:
        file_path.write_bytes(file_content)

        document = Document(
            filename=file.filename,
            file_type=extension.lstrip("."),
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        return {
            "id": document.id,
            "filename": document.filename,
            "file_type": document.file_type,
            "message": "Document uploaded successfully.",
        }

    except SQLAlchemyError:
        db.rollback()
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Could not save document metadata.",
        )

    except OSError:
        db.rollback()
        file_path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Could not save the uploaded file.",
        )
