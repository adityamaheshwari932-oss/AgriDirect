"""SQLAlchemy ORM model definitions.

Import all models here so Alembic's autogenerate can discover them.
"""

from app.models.admin import (
    ACTION_REMOVE_LISTING,
    ACTION_SUSPEND_USER,
    ACTION_VERIFY_APPROVE,
    ACTION_VERIFY_REJECT,
    CANONICAL_ADMIN_ACTIONS,
    CANONICAL_TARGET_ENTITIES,
    TARGET_ENTITY_LISTING,
    TARGET_ENTITY_REPORT,
    TARGET_ENTITY_USER,
    TARGET_ENTITY_VERIFICATION_SUBMISSION,
    AdminAuditLog,
)
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
    "AdminAuditLog",
    "ACTION_VERIFY_APPROVE",
    "ACTION_VERIFY_REJECT",
    "ACTION_SUSPEND_USER",
    "ACTION_REMOVE_LISTING",
    "CANONICAL_ADMIN_ACTIONS",
    "TARGET_ENTITY_USER",
    "TARGET_ENTITY_VERIFICATION_SUBMISSION",
    "TARGET_ENTITY_LISTING",
    "TARGET_ENTITY_REPORT",
    "CANONICAL_TARGET_ENTITIES",
]
