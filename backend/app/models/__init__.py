"""SQLAlchemy ORM model definitions.

Import all models here so Alembic's autogenerate can discover them.
"""

from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.user import BuyerProfile, FarmerProfile, User
from app.models.verification import (
    MAX_DOCUMENT_SIZE_BYTES,
    VALID_SUBMISSION_STATUSES,
    VerificationDocument,
    VerificationSubmission,
)

__all__ = [
    "UUIDPrimaryKeyMixin",
    "TimestampMixin",
    "User",
    "FarmerProfile",
    "BuyerProfile",
    "VerificationSubmission",
    "VerificationDocument",
    "VALID_SUBMISSION_STATUSES",
    "MAX_DOCUMENT_SIZE_BYTES",
]
