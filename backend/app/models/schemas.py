from datetime import datetime

from pydantic import BaseModel


class VerificationResponse(BaseModel):
    id: str
    created_at: datetime
    original_filename: str | None
    doc_type: dict | None
    quality: dict | None
    fields: dict | None
    tampering: dict | None
    decision: dict


class VerificationSummary(BaseModel):
    id: str
    created_at: datetime
    original_filename: str | None
    doc_type: str | None
    verdict: str
    reviewed: bool

    class Config:
        from_attributes = True


class ReviewOverrideRequest(BaseModel):
    verdict: str  # ACCEPT | REJECT
