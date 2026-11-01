"""Repository layer for chat threads, participants, messages, attachments, and contact requests."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_, select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.chat import (
    CONTACT_REQUEST_STATUS_PENDING,
    MESSAGE_STATUS_DELIVERED,
    MESSAGE_STATUS_READ,
    MESSAGE_STATUS_SENT,
    ContactShareRequest,
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
)


class ChatRepository:
    """Synchronous repository handling database persistence for Module 5 chat and messaging."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -------------------------------------------------------------------------
    # Conversation Operations
    # -------------------------------------------------------------------------

    def get_conversation_by_id(self, conversation_id: uuid.UUID) -> Optional[Conversation]:
        """Fetch conversation by primary key with participants and counterparties loaded."""
        stmt = (
            select(Conversation)
            .options(
                joinedload(Conversation.farmer),
                joinedload(Conversation.buyer),
                selectinload(Conversation.participants),
            )
            .where(Conversation.id == conversation_id)
        )
        return self.db.scalars(stmt).first()

    def get_conversation_between(self, farmer_id: uuid.UUID, buyer_id: uuid.UUID) -> Optional[Conversation]:
        """Fetch conversation between a specific farmer and buyer."""
        stmt = (
            select(Conversation)
            .options(
                joinedload(Conversation.farmer),
                joinedload(Conversation.buyer),
                selectinload(Conversation.participants),
            )
            .where(
                and_(
                    Conversation.farmer_id == farmer_id,
                    Conversation.buyer_id == buyer_id,
                )
            )
        )
        return self.db.scalars(stmt).first()

    def get_conversation_by_order_id(self, order_id: uuid.UUID) -> Optional[Conversation]:
        """Fetch conversation linked directly to an order ID."""
        stmt = (
            select(Conversation)
            .options(
                joinedload(Conversation.farmer),
                joinedload(Conversation.buyer),
                selectinload(Conversation.participants),
            )
            .where(Conversation.order_id == order_id)
        )
        return self.db.scalars(stmt).first()

    def create_conversation(
        self,
        farmer_id: uuid.UUID,
        buyer_id: uuid.UUID,
        initial_context_type: Optional[str] = None,
        initial_context_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
    ) -> Conversation:
        """Create a new conversation thread with initialized participant rows."""
        now_utc = datetime.now(timezone.utc)
        conversation = Conversation(
            farmer_id=farmer_id,
            buyer_id=buyer_id,
            initial_context_type=initial_context_type,
            initial_context_id=initial_context_id,
            order_id=order_id,
            created_at=now_utc,
            last_message_at=now_utc,
        )
        self.db.add(conversation)
        self.db.flush()

        # Initialize both participants with contact sharing default to False
        p_farmer = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=farmer_id,
            share_contact_details=False,
            created_at=now_utc,
        )
        p_buyer = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=buyer_id,
            share_contact_details=False,
            created_at=now_utc,
        )
        self.db.add_all([p_farmer, p_buyer])
        self.db.flush()
        return conversation

    def list_conversations_for_user(
        self,
        user_id: uuid.UUID,
        context_type: Optional[str] = None,
        order_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Conversation], int]:
        """List conversation threads for a user sorted by recent activity with total count."""
        conditions = [or_(Conversation.farmer_id == user_id, Conversation.buyer_id == user_id)]
        if context_type:
            conditions.append(Conversation.initial_context_type == context_type)
        if order_id:
            conditions.append(Conversation.order_id == order_id)

        count_stmt = select(func.count(Conversation.id)).where(and_(*conditions))
        total_count = self.db.scalar(count_stmt) or 0

        stmt = (
            select(Conversation)
            .options(
                joinedload(Conversation.farmer),
                joinedload(Conversation.buyer),
                selectinload(Conversation.participants),
            )
            .where(and_(*conditions))
            .order_by(desc(Conversation.last_message_at))
            .limit(limit)
            .offset(offset)
        )
        conversations = list(self.db.scalars(stmt).unique().all())
        return conversations, total_count

    def update_last_message_at(self, conversation_id: uuid.UUID, last_message_at: datetime) -> None:
        """Update last_message_at timestamp for a conversation."""
        self.db.execute(
            update(Conversation)
            .where(Conversation.id == conversation_id)
            .values(last_message_at=last_message_at)
        )

    # -------------------------------------------------------------------------
    # Participant Operations
    # -------------------------------------------------------------------------

    def get_participant(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> Optional[ConversationParticipant]:
        """Retrieve participant entry for a given conversation and user."""
        stmt = select(ConversationParticipant).where(
            and_(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id,
            )
        )
        return self.db.scalars(stmt).first()

    def update_participant_last_read(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, last_read_at: datetime
    ) -> None:
        """Update last read timestamp for a participant."""
        self.db.execute(
            update(ConversationParticipant)
            .where(
                and_(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id == user_id,
                )
            )
            .values(last_read_at=last_read_at)
        )

    def update_participant_contact_sharing(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID, share: bool
    ) -> None:
        """Update contact sharing consent flag for a participant."""
        self.db.execute(
            update(ConversationParticipant)
            .where(
                and_(
                    ConversationParticipant.conversation_id == conversation_id,
                    ConversationParticipant.user_id == user_id,
                )
            )
            .values(share_contact_details=share)
        )

    # -------------------------------------------------------------------------
    # Message Operations
    # -------------------------------------------------------------------------

    def create_message(
        self,
        conversation_id: uuid.UUID,
        sender_id: uuid.UUID,
        content: str,
        message_type: str = "text",
        order_id: Optional[uuid.UUID] = None,
        delivery_status: str = MESSAGE_STATUS_SENT,
    ) -> Message:
        """Persist a new message in a conversation thread."""
        now_utc = datetime.now(timezone.utc)
        message = Message(
            conversation_id=conversation_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type,
            order_id=order_id,
            delivery_status=delivery_status,
            is_read=False,
            created_at=now_utc,
        )
        self.db.add(message)
        self.db.flush()
        # Update thread last activity
        self.update_last_message_at(conversation_id, now_utc)
        return message

    def get_message_by_id(self, message_id: uuid.UUID) -> Optional[Message]:
        """Retrieve message with attachments and sender details."""
        stmt = (
            select(Message)
            .options(
                joinedload(Message.sender),
                selectinload(Message.attachments),
            )
            .where(Message.id == message_id)
        )
        return self.db.scalars(stmt).first()

    def list_messages(
        self,
        conversation_id: uuid.UUID,
        limit: int = 50,
        before_id: Optional[uuid.UUID] = None,
        after_id: Optional[uuid.UUID] = None,
        order: str = "asc",
    ) -> List[Message]:
        """Fetch messages in deterministic chronological order with optional cursor pagination."""
        stmt = (
            select(Message)
            .options(
                joinedload(Message.sender),
                selectinload(Message.attachments),
            )
            .where(Message.conversation_id == conversation_id)
        )

        if before_id:
            cursor_msg = self.get_message_by_id(before_id)
            if cursor_msg:
                stmt = stmt.where(
                    or_(
                        Message.created_at < cursor_msg.created_at,
                        and_(Message.created_at == cursor_msg.created_at, Message.id < cursor_msg.id),
                    )
                )

        if after_id:
            cursor_msg = self.get_message_by_id(after_id)
            if cursor_msg:
                stmt = stmt.where(
                    or_(
                        Message.created_at > cursor_msg.created_at,
                        and_(Message.created_at == cursor_msg.created_at, Message.id > cursor_msg.id),
                    )
                )

        if order.lower() == "desc":
            stmt = stmt.order_by(desc(Message.created_at), desc(Message.id))
        else:
            stmt = stmt.order_by(Message.created_at.asc(), Message.id.asc())

        stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).unique().all())

    def count_unread_messages(self, conversation_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Count unread messages sent by counterparties in this conversation."""
        stmt = select(func.count(Message.id)).where(
            and_(
                Message.conversation_id == conversation_id,
                Message.sender_id != user_id,
                Message.is_read.is_(False),
            )
        )
        return self.db.scalar(stmt) or 0

    def mark_messages_delivered(self, conversation_id: uuid.UUID, recipient_id: uuid.UUID) -> int:
        """Mark unread messages sent by counterparties as delivered."""
        now_utc = datetime.now(timezone.utc)
        result = self.db.execute(
            update(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.sender_id != recipient_id,
                    Message.delivery_status == MESSAGE_STATUS_SENT,
                )
            )
            .values(
                delivery_status=MESSAGE_STATUS_DELIVERED,
                delivered_at=now_utc,
            )
        )
        return result.rowcount

    def mark_messages_read(self, conversation_id: uuid.UUID, recipient_id: uuid.UUID) -> int:
        """Mark unread messages sent by counterparties as read and update recipient read timestamp."""
        now_utc = datetime.now(timezone.utc)
        result = self.db.execute(
            update(Message)
            .where(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.sender_id != recipient_id,
                    Message.is_read.is_(False),
                )
            )
            .values(
                is_read=True,
                delivery_status=MESSAGE_STATUS_READ,
                read_at=now_utc,
            )
        )
        self.update_participant_last_read(conversation_id, recipient_id, now_utc)
        return result.rowcount

    # -------------------------------------------------------------------------
    # Attachment Operations
    # -------------------------------------------------------------------------

    def create_attachment(
        self,
        message_id: uuid.UUID,
        file_uri: str,
        file_name: str,
        file_mime_type: str,
        file_size_bytes: int,
        attachment_type: str = "image",
    ) -> MessageAttachment:
        """Persist attachment metadata linked to a message."""
        now_utc = datetime.now(timezone.utc)
        attachment = MessageAttachment(
            message_id=message_id,
            file_uri=file_uri,
            file_name=file_name,
            file_mime_type=file_mime_type,
            file_size_bytes=file_size_bytes,
            attachment_type=attachment_type,
            created_at=now_utc,
        )
        self.db.add(attachment)
        self.db.flush()
        return attachment

    def get_attachment_by_id(self, attachment_id: uuid.UUID) -> Optional[MessageAttachment]:
        """Fetch attachment by ID with associated message and conversation loaded."""
        stmt = (
            select(MessageAttachment)
            .options(
                joinedload(MessageAttachment.message).joinedload(Message.conversation),
            )
            .where(MessageAttachment.id == attachment_id)
        )
        return self.db.scalars(stmt).first()

    # -------------------------------------------------------------------------
    # Contact Sharing Request Operations
    # -------------------------------------------------------------------------

    def create_contact_share_request(
        self,
        conversation_id: uuid.UUID,
        requester_id: uuid.UUID,
        recipient_id: uuid.UUID,
        notes: Optional[str] = None,
    ) -> ContactShareRequest:
        """Create a new contact sharing consent request."""
        now_utc = datetime.now(timezone.utc)
        request = ContactShareRequest(
            conversation_id=conversation_id,
            requester_id=requester_id,
            recipient_id=recipient_id,
            status=CONTACT_REQUEST_STATUS_PENDING,
            requested_at=now_utc,
            notes=notes,
        )
        self.db.add(request)
        self.db.flush()
        return request

    def get_contact_share_request_by_id(self, request_id: uuid.UUID) -> Optional[ContactShareRequest]:
        """Retrieve contact share request by ID."""
        stmt = (
            select(ContactShareRequest)
            .options(
                joinedload(ContactShareRequest.conversation),
                joinedload(ContactShareRequest.requester),
                joinedload(ContactShareRequest.recipient),
            )
            .where(ContactShareRequest.id == request_id)
        )
        return self.db.scalars(stmt).first()

    def get_active_contact_share_request(self, conversation_id: uuid.UUID) -> Optional[ContactShareRequest]:
        """Retrieve any active pending contact share request in a conversation."""
        stmt = select(ContactShareRequest).where(
            and_(
                ContactShareRequest.conversation_id == conversation_id,
                ContactShareRequest.status == CONTACT_REQUEST_STATUS_PENDING,
            )
        )
        return self.db.scalars(stmt).first()

    def list_contact_share_requests(self, conversation_id: uuid.UUID) -> List[ContactShareRequest]:
        """List all contact share requests for a conversation thread."""
        stmt = (
            select(ContactShareRequest)
            .where(ContactShareRequest.conversation_id == conversation_id)
            .order_by(desc(ContactShareRequest.requested_at))
        )
        return list(self.db.scalars(stmt).all())

    def update_contact_share_request_status(
        self,
        request: ContactShareRequest,
        status: str,
        responded_at: datetime,
    ) -> ContactShareRequest:
        """Update request status and response timestamp."""
        request.status = status
        request.responded_at = responded_at
        self.db.add(request)
        self.db.flush()
        return request

