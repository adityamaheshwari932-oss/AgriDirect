"""SQLAlchemy ORM models for contextual communication and chat threads.

Implements Module 3 (Contextual Communication) of AgriDirect:
- ``Conversation``: Direct messaging thread between a buyer and a farmer (Table 3.1 / Store D7).
- ``ConversationParticipant``: Per-user conversation settings and contact disclosure (Table 3.2 / Junction D7).
- ``Message``: Individual chat entries (Table 3.3 / Store D8).
- ``MessageAttachment``: Media and documents shared in chat (Table 3.4 / Child of D8).
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
    from app.models.user import User

# Canonical initial context types for conversations
CONTEXT_TYPE_LISTING = "listing"
CONTEXT_TYPE_REQUIREMENT = "requirement"
CONTEXT_TYPE_GENERAL = "general"

VALID_CONTEXT_TYPES = (
    CONTEXT_TYPE_LISTING,
    CONTEXT_TYPE_REQUIREMENT,
    CONTEXT_TYPE_GENERAL,
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

    __table_args__ = (
        CheckConstraint(
            "farmer_id <> buyer_id",
            name="chk_conversations_counterparts",
        ),
        UniqueConstraint(
            "farmer_id",
            "buyer_id",
            name="uq_conversations_counterparts",
        ),
        Index("idx_conversations_counterparts", "farmer_id", "buyer_id"),
        Index("idx_conversations_last_msg", text("last_message_at DESC")),
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
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
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
    attachments: Mapped[List["MessageAttachment"]] = relationship(
        "MessageAttachment",
        foreign_keys="[MessageAttachment.message_id]",
        back_populates="message",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id", "created_at"),
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
        Index("idx_msg_attachments_message", "message_id"),
    )
