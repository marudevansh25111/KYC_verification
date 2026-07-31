import uuid

from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.sql import func

from app.db.session import Base


class VerificationRecord(Base):
    """
    Audit log entry for one /verify call. Stores the full structured
    pipeline output (quality/OCR/tampering/decision) as JSON rather than
    normalizing into columns — the schema of "which fields exist" varies
    by document type, and the audit log's job is to reproduce exactly
    what a reviewer saw, not to support relational queries over field
    values.
    """
    __tablename__ = "verification_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    original_filename = Column(String(255), nullable=True)
    doc_type = Column(String(50), nullable=True)

    verdict = Column(String(20), nullable=False)  # ACCEPT | REVIEW | REJECT
    reasons = Column(JSON, nullable=False)

    quality_result = Column(JSON, nullable=True)
    fields_result = Column(JSON, nullable=True)
    tampering_result = Column(JSON, nullable=True)

    reviewed = Column(Boolean, nullable=False, default=False)
    reviewer_override_verdict = Column(String(20), nullable=True)
