import numpy as np
import cv2
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import VerificationRecord
from app.models.schemas import VerificationResponse
from app.services.pipeline import run_verification

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/jpg"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/verify", response_model=VerificationResponse)
async def verify_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {file.content_type}")

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    np_buf = np.frombuffer(raw_bytes, dtype=np.uint8)
    image_bgr = cv2.imdecode(np_buf, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise HTTPException(status_code=400, detail="Could not decode image file")

    result = run_verification(image_bgr)

    record = VerificationRecord(
        original_filename=file.filename,
        doc_type=result["doc_type"]["doc_type"],
        verdict=result["decision"]["verdict"],
        reasons=result["decision"]["reasons"],
        quality_result=result["quality"],
        fields_result=result["fields"],
        tampering_result=result["tampering"],
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return VerificationResponse(
        id=record.id,
        created_at=record.created_at,
        original_filename=record.original_filename,
        doc_type=result["doc_type"],
        quality=result["quality"],
        fields=result["fields"],
        tampering=result["tampering"],
        decision=result["decision"],
    )
