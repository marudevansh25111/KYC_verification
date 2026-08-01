from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import VerificationRecord
from app.models.schemas import VerificationResponse, VerificationSummary, ReviewOverrideRequest

router = APIRouter()


@router.get("/verifications", response_model=list[VerificationSummary])
def list_verifications(
    verdict: str | None = Query(None, description="Filter by verdict: ACCEPT | REVIEW | REJECT"),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(VerificationRecord)
    if verdict:
        query = query.filter(VerificationRecord.verdict == verdict.upper())
    records = query.order_by(VerificationRecord.created_at.desc()).limit(limit).all()
    return records


@router.get("/verifications/{record_id}", response_model=VerificationResponse)
def get_verification(record_id: str, db: Session = Depends(get_db)):
    record = db.query(VerificationRecord).filter(VerificationRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Verification record not found")

    return VerificationResponse(
        id=record.id,
        created_at=record.created_at,
        original_filename=record.original_filename,
        doc_type={"doc_type": record.doc_type, "confidence": None, "reason": None},
        quality=record.quality_result,
        fields=record.fields_result,
        tampering=record.tampering_result,
        decision={"verdict": record.reviewer_override_verdict or record.verdict, "reasons": record.reasons},
    )


@router.post("/verifications/{record_id}/review")
def review_verification(record_id: str, body: ReviewOverrideRequest, db: Session = Depends(get_db)):
    if body.verdict not in ("ACCEPT", "REJECT"):
        raise HTTPException(status_code=400, detail="verdict must be ACCEPT or REJECT")

    record = db.query(VerificationRecord).filter(VerificationRecord.id == record_id).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Verification record not found")

    record.reviewed = True
    record.reviewer_override_verdict = body.verdict
    db.commit()
    return {"id": record.id, "reviewed": True, "final_verdict": body.verdict}
