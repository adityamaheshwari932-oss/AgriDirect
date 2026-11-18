"""SQLAlchemy models for User identity and role-specialized profiles.

Implements Module 1 of AgriDirect:
- ``User``: Central authentication credentials, role, and verification lifecycle.
- ``FarmerProfile``: Farm location, acreage, farming practices, and produce capacity.
- ``BuyerProfile``: Commercial entity, trade type, and delivery receiving facilities.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from app.models.admin import AdminAuditLog
    from app.models.chat import Conversation, ConversationParticipant, Message
    from app.models.listing import ProduceListing
    from app.models.notification import Notification
    from app.models.offer import Offer
    from app.models.order import Order
    from app.models.report import UserReport
    from app.models.requirement import BuyerRequirement
    from app.models.review import RatingReview
    from app.models.verification import VerificationSubmission

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

VALID_USER_ROLES = ("farmer", "buyer", "admin", "transporter")
VALID_VERIFICATION_STATUSES = ("unverified", "pending", "verified", "rejected")
VALID_ACCOUNT_STATUSES = ("active", "restricted", "suspended", "blocked")
VALID_BUYER_TYPES = (
    "restaurant",
    "hotel",
    "retailer",
    "wholesaler",
    "food_processor",
    "caterer",
    "other",
)
VALID_TRANSPORT_TYPES = (
    "mini_truck",
    "open_body",
    "refrigerated",
    "covered_truck",
    "tempo",
    "trailer",
    "other",
)
VALID_COVERAGE_TYPES = ("pickup_only", "delivery_only", "both")


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a registered platform user across all roles (Farmer, Buyer, Admin).

    Authentication credentials, authorization role, and current verification status
    are managed here. Role-specific profile details are delegated to specialized
    1:1 child models (``FarmerProfile`` or ``BuyerProfile``).
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(32),
        unique=True,
        nullable=True,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="unverified",
        server_default="unverified",
    )
    account_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )

    # 1:1 Bidirectional Relationships with specialized profile tables
    farmer_profile: Mapped[Optional["FarmerProfile"]] = relationship(
        "FarmerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    buyer_profile: Mapped[Optional["BuyerProfile"]] = relationship(
        "BuyerProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    transporter_profile: Mapped[Optional["TransporterProfile"]] = relationship(
        "TransporterProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # 1:N Relationships with verification submissions
    verification_submissions: Mapped[List["VerificationSubmission"]] = relationship(
        "VerificationSubmission",
        foreign_keys="[VerificationSubmission.user_id]",
        back_populates="user",
        order_by="VerificationSubmission.created_at",
    )
    reviewed_verifications: Mapped[List["VerificationSubmission"]] = relationship(
        "VerificationSubmission",
        foreign_keys="[VerificationSubmission.reviewed_by_admin_id]",
        back_populates="admin_reviewer",
        order_by="VerificationSubmission.reviewed_at",
    )
    admin_audit_logs: Mapped[List["AdminAuditLog"]] = relationship(
        "AdminAuditLog",
        foreign_keys="[AdminAuditLog.admin_user_id]",
        back_populates="admin_user",
        order_by="AdminAuditLog.created_at.desc()",
    )
    listings: Mapped[List["ProduceListing"]] = relationship(
        "ProduceListing",
        foreign_keys="[ProduceListing.farmer_id]",
        back_populates="farmer",
        order_by="ProduceListing.created_at.desc()",
    )
    requirements: Mapped[List["BuyerRequirement"]] = relationship(
        "BuyerRequirement",
        foreign_keys="[BuyerRequirement.buyer_id]",
        back_populates="buyer",
        order_by="BuyerRequirement.created_at.desc()",
    )
    conversations_as_farmer: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        foreign_keys="[Conversation.farmer_id]",
        back_populates="farmer",
        order_by="Conversation.created_at.desc()",
    )
    conversations_as_buyer: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        foreign_keys="[Conversation.buyer_id]",
        back_populates="buyer",
        order_by="Conversation.created_at.desc()",
    )
    conversation_participations: Mapped[List["ConversationParticipant"]] = relationship(
        "ConversationParticipant",
        foreign_keys="[ConversationParticipant.user_id]",
        back_populates="user",
    )
    sent_messages: Mapped[List["Message"]] = relationship(
        "Message",
        foreign_keys="[Message.sender_id]",
        back_populates="sender",
        order_by="Message.created_at.desc()",
    )
    sent_offers: Mapped[List["Offer"]] = relationship(
        "Offer",
        foreign_keys="[Offer.sender_id]",
        back_populates="sender",
        order_by="Offer.created_at.desc()",
    )
    received_offers: Mapped[List["Offer"]] = relationship(
        "Offer",
        foreign_keys="[Offer.recipient_id]",
        back_populates="recipient",
        order_by="Offer.created_at.desc()",
    )
    orders_as_buyer: Mapped[List["Order"]] = relationship(
        "Order",
        foreign_keys="[Order.buyer_id]",
        back_populates="buyer",
        order_by="Order.created_at.desc()",
    )
    orders_as_farmer: Mapped[List["Order"]] = relationship(
        "Order",
        foreign_keys="[Order.farmer_id]",
        back_populates="farmer",
        order_by="Order.created_at.desc()",
    )
    orders_as_transporter: Mapped[List["Order"]] = relationship(
        "Order",
        foreign_keys="[Order.transporter_id]",
        back_populates="transporter",
        order_by="Order.created_at.desc()",
    )
    reviews_given: Mapped[List["RatingReview"]] = relationship(
        "RatingReview",
        foreign_keys="[RatingReview.reviewer_id]",
        back_populates="reviewer",
        order_by="RatingReview.created_at.desc()",
    )
    reviews_received: Mapped[List["RatingReview"]] = relationship(
        "RatingReview",
        foreign_keys="[RatingReview.reviewed_user_id]",
        back_populates="reviewed_user",
        order_by="RatingReview.created_at.desc()",
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        foreign_keys="[Notification.user_id]",
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="Notification.created_at.desc()",
    )
    reports_filed: Mapped[List["UserReport"]] = relationship(
        "UserReport",
        foreign_keys="[UserReport.reporter_id]",
        back_populates="reporter",
        order_by="UserReport.created_at.desc()",
    )
    reports_received: Mapped[List["UserReport"]] = relationship(
        "UserReport",
        foreign_keys="[UserReport.reported_user_id]",
        back_populates="reported_user",
        order_by="UserReport.created_at.desc()",
    )


    __table_args__ = (
        CheckConstraint(
            "role IN ('farmer', 'buyer', 'admin', 'transporter')",
            name="chk_users_role",
        ),
        CheckConstraint(
            "verification_status IN ('unverified', 'pending', 'verified', 'rejected')",
            name="chk_users_verification_status",
        ),
        CheckConstraint(
            "account_status IN ('active', 'restricted', 'suspended', 'blocked')",
            name="chk_users_account_status",
        ),
        Index(
            "idx_users_role_status",
            "role",
            "verification_status",
            "account_status",
        ),
    )

    @validates("role")
    def validate_role(self, key: str, value: str) -> str:
        """Validate that role matches permitted values and is consistent with attached profiles."""
        if value not in VALID_USER_ROLES:
            raise ValueError(
                f"Invalid role '{value}'. Must be one of: {', '.join(VALID_USER_ROLES)}"
            )
        if value != "farmer" and getattr(self, "farmer_profile", None) is not None:
            raise ValueError(
                f"Cannot change role to '{value}' while FarmerProfile is attached."
            )
        if value != "buyer" and getattr(self, "buyer_profile", None) is not None:
            raise ValueError(
                f"Cannot change role to '{value}' while BuyerProfile is attached."
            )
        if value != "transporter" and getattr(self, "transporter_profile", None) is not None:
            raise ValueError(
                f"Cannot change role to '{value}' while TransporterProfile is attached."
            )
        return value

    @validates("verification_status")
    def validate_verification_status(self, key: str, value: str) -> str:
        """Validate that verification_status matches permitted states."""
        if value not in VALID_VERIFICATION_STATUSES:
            raise ValueError(
                f"Invalid verification_status '{value}'. Must be one of: "
                f"{', '.join(VALID_VERIFICATION_STATUSES)}"
            )
        return value

    @validates("account_status")
    def validate_account_status(self, key: str, value: str) -> str:
        """Validate that account_status matches permitted states."""
        if value not in VALID_ACCOUNT_STATUSES:
            raise ValueError(
                f"Invalid account_status '{value}'. Must be one of: "
                f"{', '.join(VALID_ACCOUNT_STATUSES)}"
            )
        return value

    @validates("farmer_profile")
    def validate_farmer_profile(
        self, key: str, profile: Optional["FarmerProfile"]
    ) -> Optional["FarmerProfile"]:
        """Enforce role/profile consistency: only farmers may have a FarmerProfile."""
        if profile is not None and self.role != "farmer":
            raise ValueError(
                f"Cannot attach FarmerProfile to user with role '{self.role}'. "
                "FarmerProfile requires role='farmer'."
            )
        return profile

    @validates("buyer_profile")
    def validate_buyer_profile(
        self, key: str, profile: Optional["BuyerProfile"]
    ) -> Optional["BuyerProfile"]:
        """Enforce role/profile consistency: only buyers may have a BuyerProfile."""
        if profile is not None and self.role != "buyer":
            raise ValueError(
                f"Cannot attach BuyerProfile to user with role '{self.role}'. "
                "BuyerProfile requires role='buyer'."
            )
        return profile

    @validates("transporter_profile")
    def validate_transporter_profile(
        self, key: str, profile: Optional["TransporterProfile"]
    ) -> Optional["TransporterProfile"]:
        """Enforce role/profile consistency: only transporters may have a TransporterProfile."""
        if profile is not None and self.role != "transporter":
            raise ValueError(
                f"Cannot attach TransporterProfile to user with role '{self.role}'. "
                "TransporterProfile requires role='transporter'."
            )
        return profile

    def __repr__(self) -> str:
        """Safe representation excluding password hash to protect credentials from logs."""
        return (
            f"<User id={self.id} email={self.email!r} role={self.role!r} "
            f"verification_status={self.verification_status!r} "
            f"account_status={self.account_status!r}>"
        )


class FarmerProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Maintains farm location, acreage, farming practices, and agricultural details.

    Associated 1:1 with a User whose role is 'farmer'.
    """

    __tablename__ = "farmer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    farm_name: Mapped[str] = mapped_column(String(128), nullable=False)
    farm_location_address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(16), nullable=False)

    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    farm_size_acres: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    farming_practices: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    primary_crops: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 1:1 Back-reference to User (deleting profile does not delete user)
    user: Mapped["User"] = relationship("User", back_populates="farmer_profile")

    __table_args__ = (
        CheckConstraint(
            "farm_size_acres IS NULL OR farm_size_acres > 0",
            name="chk_farmer_size_positive",
        ),
        Index("idx_farmer_profiles_location", "state", "city"),
    )

    @validates("user")
    def validate_user_role(self, key: str, user: Optional["User"]) -> Optional["User"]:
        """Enforce role/profile consistency when user is assigned to FarmerProfile."""
        if user is not None and user.role != "farmer":
            raise ValueError(
                f"FarmerProfile can only be associated with a user having role='farmer', "
                f"got role='{user.role}'."
            )
        return user

    @validates("farm_size_acres")
    def validate_farm_size(
        self, key: str, value: Optional[Decimal]
    ) -> Optional[Decimal]:
        """Ensure farm size is strictly positive if specified."""
        if value is not None and value <= 0:
            raise ValueError("farm_size_acres must be strictly positive.")
        return value

    def __repr__(self) -> str:
        return (
            f"<FarmerProfile id={self.id} user_id={self.user_id} "
            f"farm_name={self.farm_name!r} city={self.city!r} state={self.state!r}>"
        )


class BuyerProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Maintains commercial enterprise identity, buyer category, and delivery receiving facilities.

    Associated 1:1 with a User whose role is 'buyer'.
    """

    __tablename__ = "buyer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    contact_person_name: Mapped[str] = mapped_column(String(128), nullable=False)
    business_name: Mapped[str] = mapped_column(String(128), nullable=False)
    business_type: Mapped[str] = mapped_column(String(64), nullable=False)
    business_registration_number: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )
    delivery_receiving_address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(64), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(16), nullable=False)

    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(9, 6), nullable=True)
    procurement_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 1:1 Back-reference to User (deleting profile does not delete user)
    user: Mapped["User"] = relationship("User", back_populates="buyer_profile")

    __table_args__ = (
        CheckConstraint(
            "business_type IN ('restaurant', 'hotel', 'retailer', 'wholesaler', 'food_processor', 'caterer', 'other')",
            name="chk_buyer_business_type",
        ),
        Index("idx_buyer_profiles_business_type", "business_type"),
        Index("idx_buyer_profiles_location", "state", "city"),
    )

    @validates("user")
    def validate_user_role(self, key: str, user: Optional["User"]) -> Optional["User"]:
        """Enforce role/profile consistency when user is assigned to BuyerProfile."""
        if user is not None and user.role != "buyer":
            raise ValueError(
                f"BuyerProfile can only be associated with a user having role='buyer', "
                f"got role='{user.role}'."
            )
        return user

    @validates("business_type")
    def validate_business_type(self, key: str, value: str) -> str:
        """Ensure business_type matches permitted commercial categories."""
        if value not in VALID_BUYER_TYPES:
            raise ValueError(
                f"Invalid business_type '{value}'. Must be one of: {', '.join(VALID_BUYER_TYPES)}"
            )
        return value

    def __repr__(self) -> str:
        return (
            f"<BuyerProfile id={self.id} user_id={self.user_id} "
            f"business_name={self.business_name!r} business_type={self.business_type!r} "
            f"city={self.city!r} state={self.state!r}>"
        )


class TransporterProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Maintains commercial transportation service provider profile and fleet details.

    Associated 1:1 with a User whose role is 'transporter'.
    """

    __tablename__ = "transporter_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    business_name: Mapped[str] = mapped_column(String(128), nullable=False)
    contact_name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    transport_type: Mapped[str] = mapped_column(String(64), nullable=False)
    vehicle_capacity_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    vehicle_registration_number: Mapped[str] = mapped_column(String(64), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    experience_years: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    operating_states: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 1:1 Back-reference to User
    user: Mapped["User"] = relationship("User", back_populates="transporter_profile")

    # 1:N Relationship to ServiceArea
    service_areas: Mapped[List["ServiceArea"]] = relationship(
        "ServiceArea",
        back_populates="transporter_profile",
        cascade="all, delete-orphan",
        order_by="ServiceArea.created_at.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "vehicle_capacity_kg > 0",
            name="chk_transporter_capacity_positive",
        ),
        CheckConstraint(
            "experience_years >= 0",
            name="chk_transporter_exp_non_negative",
        ),
        Index("idx_transporter_profiles_type_available", "transport_type", "is_available"),
    )

    @validates("user")
    def validate_user_role(self, key: str, user: Optional["User"]) -> Optional["User"]:
        """Enforce role/profile consistency when user is assigned to TransporterProfile."""
        if user is not None and user.role != "transporter":
            raise ValueError(
                f"TransporterProfile can only be associated with a user having role='transporter', "
                f"got role='{user.role}'."
            )
        return user

    @validates("vehicle_capacity_kg")
    def validate_vehicle_capacity(
        self, key: str, value: Decimal
    ) -> Decimal:
        if value is not None and value <= 0:
            raise ValueError("vehicle_capacity_kg must be strictly positive.")
        return value

    def __repr__(self) -> str:
        return (
            f"<TransporterProfile id={self.id} user_id={self.user_id} "
            f"business_name={self.business_name!r} transport_type={self.transport_type!r} "
            f"capacity={self.vehicle_capacity_kg}kg>"
        )


class ServiceArea(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Geographic service area serviceable by a transporter.

    Allows transporters to declare pickup and/or delivery coverage by state, district,
    taluka, village/town, and pincode.
    """

    __tablename__ = "service_areas"

    transporter_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporter_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    district: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    taluka_subdistrict: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    village_town: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, index=True)
    coverage_type: Mapped[str] = mapped_column(
        String(32),
        default="both",
        server_default="both",
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    # N:1 Back-reference to TransporterProfile
    transporter_profile: Mapped["TransporterProfile"] = relationship(
        "TransporterProfile",
        back_populates="service_areas",
    )

    __table_args__ = (
        CheckConstraint(
            "coverage_type IN ('pickup_only', 'delivery_only', 'both')",
            name="chk_service_area_coverage_type",
        ),
        UniqueConstraint(
            "transporter_profile_id",
            "state",
            "district",
            "coverage_type",
            name="uq_service_area_profile_location",
        ),
        Index("idx_service_areas_state_district", "state", "district"),
    )

    @validates("coverage_type")
    def validate_coverage_type(self, key: str, value: str) -> str:
        valid_types = ("pickup_only", "delivery_only", "both")
        if value not in valid_types:
            raise ValueError(
                f"Invalid coverage_type '{value}'. Must be one of: {', '.join(valid_types)}"
            )
        return value

    def __repr__(self) -> str:
        return (
            f"<ServiceArea id={self.id} transporter_id={self.transporter_profile_id} "
            f"state={self.state!r} district={self.district!r} type={self.coverage_type!r}>"
        )
