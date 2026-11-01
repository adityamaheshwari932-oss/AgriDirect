"""SQLAlchemy ORM models for contextual communication, chat threads, and attachments.

Implements Module 5 (Messaging and Communication System) of AgriDirect:
- ``Conversation``: Direct messaging thread between a buyer and a farmer (Table 3.1 / Store D7).
- ``ConversationParticipant``: Per-user conversation settings and contact disclosure (Table 3.2 / Junction D7).
- ``Message``: Individual chat entries with status and optional order linkage (Table 3.3 / Store D8).
- ``MessageAttachment``: Media (images) and documents shared in chat (Table 3.4 / Child of D8).
- ``ContactShareRequest``: Mutual consent workflow for disclosing contact details (Table 3.5).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.offer import Offer
    from app.models.order import Order
    from app.models.user import User

# Canonical initial context types for conversations
CONTEXT_TYPE_LISTING = "listing"
CONTEXT_TYPE_REQUIREMENT = "requirement"
CONTEXT_TYPE_OFFER = "offer"
CONTEXT_TYPE_ORDER = "order"
CONTEXT_TYPE_GENERAL = "general"

VALID_CONTEXT_TYPES = (
    CONTEXT_TYPE_LISTING,
    CONTEXT_TYPE_REQUIREMENT,
    CONTEXT_TYPE_OFFER,
    CONTEXT_TYPE_ORDER,
    CONTEXT_TYPE_GENERAL,
)

CONVERSATION_STATUS_ACTIVE = "active"
CONVERSATION_STATUS_ARCHIVED = "archived"
VALID_CONVERSATION_STATUSES = (
    CONVERSATION_STATUS_ACTIVE,
    CONVERSATION_STATUS_ARCHIVED,
)

MESSAGE_TYPE_TEXT = "text"
MESSAGE_TYPE_SYSTEM = "system"
MESSAGE_TYPE_CONTACT_REQUEST = "contact_request"
VALID_MESSAGE_TYPES = (
    MESSAGE_TYPE_TEXT,
    MESSAGE_TYPE_SYSTEM,
    MESSAGE_TYPE_CONTACT_REQUEST,
)

MESSAGE_STATUS_SENT = "sent"
MESSAGE_STATUS_DELIVERED = "delivered"
MESSAGE_STATUS_READ = "read"
VALID_MESSAGE_STATUSES = (
    MESSAGE_STATUS_SENT,
    MESSAGE_STATUS_DELIVERED,
    MESSAGE_STATUS_READ,
)

ATTACHMENT_TYPE_IMAGE = "image"
ATTACHMENT_TYPE_DOCUMENT = "document"
VALID_ATTACHMENT_TYPES = (
    ATTACHMENT_TYPE_IMAGE,
    ATTACHMENT_TYPE_DOCUMENT,
)

CONTACT_REQUEST_STATUS_PENDING = "pending"
CONTACT_REQUEST_STATUS_APPROVED = "approved"
CONTACT_REQUEST_STATUS_REJECTED = "rejected"
CONTACT_REQUEST_STATUS_CANCELLED = "cancelled"
VALID_CONTACT_REQUEST_STATUSES = (
    CONTACT_REQUEST_STATUS_PENDING,
    CONTACT_REQUEST_STATUS_APPROVED,
    CONTACT_REQUEST_STATUS_REJECTED,
    CONTACT_REQUEST_STATUS_CANCELLED,
)


class Conversation(Base, UUIDPrimaryKeyMixin):
    """Direct messaging thread between a commercial buyer and a farmer.

    Reusable across multiple transactions and products, preserving conversation continuity.
    Maintains cached last_message_at for rapid inbox sorting.
    """

    __tablename__ = "conversations"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    initial_context_type: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    initial_context_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL", use_alter=True, name="fk_conversations_order_id"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=CONVERSATION_STATUS_ACTIVE,
        server_default=CONVERSATION_STATUS_ACTIVE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    farmer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[farmer_id],
        back_populates="conversations_as_farmer",
    )
    buyer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="conversations_as_buyer",
    )
    participants: Mapped[List["ConversationParticipant"]] = relationship(
        "ConversationParticipant",
        foreign_keys="[ConversationParticipant.conversation_id]",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    messages: Mapped[List["Message"]] = relationship(
        "Message",
        foreign_keys="[Message.conversation_id]",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at.asc()",
    )
    offers: Mapped[List["Offer"]] = relationship(
        "Offer",
        foreign_keys="[Offer.conversation_id]",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Offer.created_at.desc()",
    )
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[order_id],
    )
    contact_requests: Mapped[List["ContactShareRequest"]] = relationship(
        "ContactShareRequest",
        foreign_keys="[ContactShareRequest.conversation_id]",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ContactShareRequest.requested_at.desc()",
    )

    __table_args__ = (
        CheckConstraint(
            "farmer_id <> buyer_id",
            name="chk_conversations_counterparts",
        ),
        CheckConstraint(
            f"status IN ('{CONVERSATION_STATUS_ACTIVE}', '{CONVERSATION_STATUS_ARCHIVED}')",
            name="chk_conversations_status",
        ),
        UniqueConstraint(
            "farmer_id",
            "buyer_id",
            name="uq_conversations_counterparts",
        ),
        Index("idx_conversations_counterparts", "farmer_id", "buyer_id"),
        Index("idx_conversations_last_msg", text("last_message_at DESC")),
        Index("idx_conversations_order_id", "order_id"),
    )


class ConversationParticipant(Base, UUIDPrimaryKeyMixin):
    """Maintains per-user conversation settings, unread tracking, and contact privacy disclosure."""

    __tablename__ = "conversation_participants"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    share_contact_details: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    last_read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
        back_populates="participants",
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="conversation_participations",
    )

    __table_args__ = (
        UniqueConstraint(
            "conversation_id",
            "user_id",
            name="uq_conversation_participants",
        ),
    )


class Message(Base, UUIDPrimaryKeyMixin):
    """Individual chat entries within a conversation thread."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    message_type: Mapped[str] = mapped_column(
        String(32),
        default=MESSAGE_TYPE_TEXT,
        server_default=MESSAGE_TYPE_TEXT,
        nullable=False,
    )
    delivery_status: Mapped[str] = mapped_column(
        String(32),
        default=MESSAGE_STATUS_SENT,
        server_default=MESSAGE_STATUS_SENT,
        nullable=False,
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    read_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL", use_alter=True, name="fk_conversations_order_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
        back_populates="messages",
    )
    sender: Mapped["User"] = relationship(
        "User",
        foreign_keys=[sender_id],
        back_populates="sent_messages",
    )
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        foreign_keys=[order_id],
    )
    attachments: Mapped[List["MessageAttachment"]] = relationship(
        "MessageAttachment",
        foreign_keys="[MessageAttachment.message_id]",
        back_populates="message",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            f"delivery_status IN ('{MESSAGE_STATUS_SENT}', '{MESSAGE_STATUS_DELIVERED}', '{MESSAGE_STATUS_READ}')",
            name="chk_messages_delivery_status",
        ),
        CheckConstraint(
            f"message_type IN ('{MESSAGE_TYPE_TEXT}', '{MESSAGE_TYPE_SYSTEM}', '{MESSAGE_TYPE_CONTACT_REQUEST}')",
            name="chk_messages_type",
        ),
        Index("idx_messages_conversation", "conversation_id", "created_at"),
        Index("idx_messages_status", "conversation_id", "delivery_status"),
        Index("idx_messages_order_id", "order_id"),
    )


class MessageAttachment(Base, UUIDPrimaryKeyMixin):
    """Media and documents shared in chat."""

    __tablename__ = "message_attachments"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_uri: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    file_mime_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    file_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    attachment_type: Mapped[str] = mapped_column(
        String(32),
        default=ATTACHMENT_TYPE_IMAGE,
        server_default=ATTACHMENT_TYPE_IMAGE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    message: Mapped["Message"] = relationship(
        "Message",
        foreign_keys=[message_id],
        back_populates="attachments",
    )

    __table_args__ = (
        CheckConstraint(
            "file_size_bytes > 0",
            name="chk_msg_attachments_file_size",
        ),
        CheckConstraint(
            f"attachment_type IN ('{ATTACHMENT_TYPE_IMAGE}', '{ATTACHMENT_TYPE_DOCUMENT}')",
            name="chk_msg_attachments_type",
        ),
        Index("idx_msg_attachments_message", "message_id"),
    )


class ContactShareRequest(Base, UUIDPrimaryKeyMixin):
    """Manages mutual consent workflow for disclosing contact information in a conversation."""

    __tablename__ = "contact_share_requests"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recipient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=CONTACT_REQUEST_STATUS_PENDING,
        server_default=CONTACT_REQUEST_STATUS_PENDING,
        nullable=False,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        foreign_keys=[conversation_id],
        back_populates="contact_requests",
    )
    requester: Mapped["User"] = relationship(
        "User",
        foreign_keys=[requester_id],
    )
    recipient: Mapped["User"] = relationship(
        "User",
        foreign_keys=[recipient_id],
    )

    __table_args__ = (
        CheckConstraint(
            "requester_id <> recipient_id",
            name="chk_contact_share_counterparts",
        ),
        CheckConstraint(
            f"status IN ('{CONTACT_REQUEST_STATUS_PENDING}', '{CONTACT_REQUEST_STATUS_APPROVED}', '{CONTACT_REQUEST_STATUS_REJECTED}', '{CONTACT_REQUEST_STATUS_CANCELLED}')",
            name="chk_contact_share_status",
        ),
        Index("idx_contact_share_conv_status", "conversation_id", "status"),
        Index("idx_contact_share_recipient_status", "recipient_id", "status"),
    )
