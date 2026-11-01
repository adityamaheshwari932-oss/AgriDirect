"""Service layer for chat threads, messaging, attachments, contact sharing, and status tracking."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.chat.repository import ChatRepository
from app.chat.storage import ChatStorageService
from app.models.chat import (
    ATTACHMENT_TYPE_DOCUMENT,
    ATTACHMENT_TYPE_IMAGE,
    CONTACT_REQUEST_STATUS_APPROVED,
    CONTACT_REQUEST_STATUS_CANCELLED,
    CONTACT_REQUEST_STATUS_PENDING,
    CONTACT_REQUEST_STATUS_REJECTED,
    CONTEXT_TYPE_GENERAL,
    CONTEXT_TYPE_LISTING,
    CONTEXT_TYPE_OFFER,
    CONTEXT_TYPE_ORDER,
    CONTEXT_TYPE_REQUIREMENT,
    CONVERSATION_STATUS_ACTIVE,
    MESSAGE_STATUS_DELIVERED,
    MESSAGE_STATUS_READ,
    MESSAGE_STATUS_SENT,
    MESSAGE_TYPE_CONTACT_REQUEST,
    MESSAGE_TYPE_SYSTEM,
    MESSAGE_TYPE_TEXT,
    ContactShareRequest,
    Conversation,
    ConversationParticipant,
    Message,
    MessageAttachment,
)
from app.models.listing import STATUS_ACTIVE, STATUS_PARTIALLY_FULFILLED, ProduceListing
from app.models.offer import Offer
from app.models.order import Order
from app.models.requirement import REQUIREMENT_STATUS_ACTIVE, BuyerRequirement
from app.models.user import BuyerProfile, FarmerProfile, User

MAX_MESSAGE_LENGTH: int = 5000


class ChatService:
    """Encapsulates all business logic and security policies for AgriDirect Module 5."""

    def __init__(self, db: Session, storage_service: Optional[ChatStorageService] = None) -> None:
        self.db = db
        self.repo = ChatRepository(db)
        self.storage = storage_service or ChatStorageService()

    # -------------------------------------------------------------------------
    # M5-01: Conversation Creation & Validation
    # -------------------------------------------------------------------------

    def create_or_get_conversation(
        self,
        current_user: User,
        target_user_id: Optional[uuid.UUID] = None,
        listing_id: Optional[uuid.UUID] = None,
        requirement_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        offer_id: Optional[uuid.UUID] = None,
    ) -> Tuple[Conversation, bool]:
        """Create or retrieve a conversation thread based on marketplace context.

        Returns:
            Tuple of (conversation: Conversation, created: bool).
        """
        # User account status check
        if current_user.account_status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is suspended or inactive",
            )

        context_type: Optional[str] = None
        context_id: Optional[uuid.UUID] = None
        farmer_id: Optional[uuid.UUID] = None
        buyer_id: Optional[uuid.UUID] = None

        # 1. Order Context
        if order_id:
            order = self.db.query(Order).filter(Order.id == order_id).first()
            if not order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced order not found",
                )
            if current_user.id not in (order.farmer_id, order.buyer_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced order not found or user is not authorized",
                )
            farmer_id = order.farmer_id
            buyer_id = order.buyer_id
            context_type = CONTEXT_TYPE_ORDER
            context_id = order.id

        # 2. Offer Context
        elif offer_id:
            offer = self.db.query(Offer).filter(Offer.id == offer_id).first()
            if not offer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced offer not found",
                )
            if current_user.id not in (offer.sender_id, offer.recipient_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced offer not found or user is not authorized",
                )
            # Determine farmer and buyer from offer sender/recipient roles
            u1 = self.db.query(User).filter(User.id == offer.sender_id).first()
            u2 = self.db.query(User).filter(User.id == offer.recipient_id).first()
            if u1 and u1.role == "farmer":
                farmer_id = u1.id
                buyer_id = u2.id if u2 else None
            elif u2 and u2.role == "farmer":
                farmer_id = u2.id
                buyer_id = u1.id if u1 else None
            context_type = CONTEXT_TYPE_OFFER
            context_id = offer.id

        # 3. Listing Context
        elif listing_id:
            listing = self.db.query(ProduceListing).filter(ProduceListing.id == listing_id).first()
            if not listing or getattr(listing, "is_deleted", False):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced listing not found or is unavailable",
                )
            if listing.status not in (STATUS_ACTIVE, STATUS_PARTIALLY_FULFILLED):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot initiate conversation on listing with status '{listing.status}'",
                )
            farmer_id = listing.farmer_id
            if current_user.role == "buyer":
                buyer_id = current_user.id
            elif current_user.role == "farmer":
                if current_user.id != listing.farmer_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot initiate conversation on another farmer's listing",
                    )
                if not target_user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Target buyer must be specified when farmer initiates from listing",
                    )
                buyer_id = target_user_id
            context_type = CONTEXT_TYPE_LISTING
            context_id = listing.id

        # 4. Requirement Context
        elif requirement_id:
            req = self.db.query(BuyerRequirement).filter(BuyerRequirement.id == requirement_id).first()
            if not req or getattr(req, "is_deleted", False):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced buyer requirement not found or is unavailable",
                )
            if req.status != REQUIREMENT_STATUS_ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot initiate conversation on requirement with status '{req.status}'",
                )
            buyer_id = req.buyer_id
            if current_user.role == "farmer":
                # Only verified farmers can respond to buyer requirements
                if current_user.verification_status != "verified":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only verified farmers are permitted to respond to buyer requirements",
                    )
                farmer_id = current_user.id
            elif current_user.role == "buyer":
                if current_user.id != req.buyer_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot initiate conversation on another buyer's requirement",
                    )
                if not target_user_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Target farmer must be specified when buyer initiates from requirement",
                    )
                farmer_id = target_user_id
            context_type = CONTEXT_TYPE_REQUIREMENT
            context_id = req.id

        # 5. Direct / General Context
        elif target_user_id:
            target_user = self.db.query(User).filter(User.id == target_user_id).first()
            if not target_user or target_user.account_status != "active":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Target user not found or unavailable",
                )
            # Commercial buyers must have a marketplace context to initiate conversations
            if current_user.role == "buyer":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Buyers must provide a marketplace context (listing, requirement, order, or offer) to initiate conversations",
                )
            if current_user.role == "farmer":
                farmer_id = current_user.id
                buyer_id = target_user.id
            else:
                farmer_id = target_user.id
                buyer_id = current_user.id
            context_type = CONTEXT_TYPE_GENERAL
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must provide marketplace context (listing_id, requirement_id, order_id, offer_id) or target user",
            )

        if not farmer_id or not buyer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not establish valid farmer and buyer participants for conversation",
            )

        # Self-conversation prevention check
        if farmer_id == buyer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Users cannot create a conversation with themselves",
            )

        # Ensure farmer is actually a farmer and buyer is actually a buyer
        farmer_user = self.db.query(User).filter(User.id == farmer_id).first()
        buyer_user = self.db.query(User).filter(User.id == buyer_id).first()
        if not farmer_user or farmer_user.role != "farmer":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Participant designated as farmer is not a registered farmer",
            )
        if not buyer_user or buyer_user.role != "buyer":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Participant designated as buyer is not a registered buyer",
            )

        # Check for existing canonical conversation between counterparts
        existing = self.repo.get_conversation_between(farmer_id, buyer_id)
        if existing:
            # If order_id was specified and thread has none, link it
            if order_id and not existing.order_id:
                existing.order_id = order_id
                self.db.add(existing)
                self.db.commit()
            return existing, False

        # Create new conversation with race-condition handling
        try:
            conversation = self.repo.create_conversation(
                farmer_id=farmer_id,
                buyer_id=buyer_id,
                initial_context_type=context_type,
                initial_context_id=context_id,
                order_id=order_id,
            )
            self.db.commit()
            return conversation, True
        except Exception:
            self.db.rollback()
            existing = self.repo.get_conversation_between(farmer_id, buyer_id)
            if existing:
                if order_id and not existing.order_id:
                    existing.order_id = order_id
                    self.db.add(existing)
                    self.db.commit()
                return existing, False
            raise

    # -------------------------------------------------------------------------
    # M5-02: Conversation Retrieval & Participant Privacy
    # -------------------------------------------------------------------------

    def list_conversations(
        self,
        current_user: User,
        context_type: Optional[str] = None,
        order_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List conversation threads for current user with unread counts and context summaries."""
        conversations, total = self.repo.list_conversations_for_user(
            user_id=current_user.id,
            context_type=context_type,
            order_id=order_id,
            limit=limit,
            offset=offset,
        )

        results = []
        for conv in conversations:
            unread = self.repo.count_unread_messages(conv.id, current_user.id)
            other_user = conv.buyer if current_user.id == conv.farmer_id else conv.farmer
            last_msg = (
                self.db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc())
                .first()
            )

            # Check if contact sharing is permitted
            has_consent = self._has_contact_sharing_consent(conv.id)
            other_user_info = self._format_user_info(other_user, disclose_contact=has_consent)

            results.append(
                {
                    "id": conv.id,
                    "farmer_id": conv.farmer_id,
                    "buyer_id": conv.buyer_id,
                    "initial_context_type": conv.initial_context_type,
                    "initial_context_id": conv.initial_context_id,
                    "order_id": conv.order_id,
                    "status": conv.status,
                    "created_at": conv.created_at,
                    "last_message_at": conv.last_message_at,
                    "unread_count": unread,
                    "other_participant": other_user_info,
                    "last_message_preview": last_msg.content[:100] if last_msg else None,
                }
            )
        return results, total

    def get_conversation_details(self, conversation_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        """Retrieve conversation detail view with anti-enumeration check and contact privacy disclosure."""
        conv = self.repo.get_conversation_by_id(conversation_id)
        if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation thread not found",
            )

        unread = self.repo.count_unread_messages(conv.id, current_user.id)
        has_consent = self._has_contact_sharing_consent(conv.id)
        other_user = conv.buyer if current_user.id == conv.farmer_id else conv.farmer
        other_user_info = self._format_user_info(other_user, disclose_contact=has_consent)

        active_request = self.repo.get_active_contact_share_request(conv.id)

        return {
            "id": conv.id,
            "farmer_id": conv.farmer_id,
            "buyer_id": conv.buyer_id,
            "initial_context_type": conv.initial_context_type,
            "initial_context_id": conv.initial_context_id,
            "order_id": conv.order_id,
            "status": conv.status,
            "created_at": conv.created_at,
            "last_message_at": conv.last_message_at,
            "unread_count": unread,
            "other_participant": other_user_info,
            "contact_sharing_consented": has_consent,
            "active_contact_request": (
                {
                    "id": active_request.id,
                    "requester_id": active_request.requester_id,
                    "status": active_request.status,
                    "requested_at": active_request.requested_at,
                }
                if active_request
                else None
            ),
        }

    # -------------------------------------------------------------------------
    # M5-03 & M5-04: Messaging & Message History
    # -------------------------------------------------------------------------

    def send_message(
        self,
        conversation_id: uuid.UUID,
        current_user: User,
        content: str,
        message_type: str = MESSAGE_TYPE_TEXT,
        order_id: Optional[uuid.UUID] = None,
    ) -> Message:
        """Validate content, authorization, and persist a text message."""
        conv = self.repo.get_conversation_by_id(conversation_id)
        if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation thread not found",
            )

        cleaned_content = (content or "").strip()
        if not cleaned_content:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Message content cannot be empty or whitespace only",
            )

        if len(cleaned_content) > MAX_MESSAGE_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"Message exceeds maximum allowed length of {MAX_MESSAGE_LENGTH} characters",
            )

        if order_id:
            order = self.db.query(Order).filter(Order.id == order_id).first()
            if not order or current_user.id not in (order.farmer_id, order.buyer_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Referenced order not found or user is not authorized",
                )

        message = self.repo.create_message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            content=cleaned_content,
            message_type=message_type,
            order_id=order_id,
            delivery_status=MESSAGE_STATUS_SENT,
        )
        self.db.commit()
        return message

    def list_messages(
        self,
        conversation_id: uuid.UUID,
        current_user: User,
        limit: int = 50,
        before_id: Optional[uuid.UUID] = None,
        after_id: Optional[uuid.UUID] = None,
        order: str = "asc",
    ) -> List[Message]:
        """Retrieve paginated messages for a conversation and mark pending counterparty messages as delivered."""
        conv = self.repo.get_conversation_by_id(conversation_id)
        if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation thread not found",
            )

        messages = self.repo.list_messages(
            conversation_id=conversation_id,
            limit=limit,
            before_id=before_id,
            after_id=after_id,
            order=order,
        )

        # Mark any newly retrieved messages from counterparty as DELIVERED
        self.repo.mark_messages_delivered(conversation_id, current_user.id)
        self.db.commit()
        return messages

    # -------------------------------------------------------------------------
    # M5-05, M5-06, M5-11: Attachments & Security
    # -------------------------------------------------------------------------

    def upload_attachment_for_message(
        self,
        conversation_id: uuid.UUID,
        message_id: uuid.UUID,
        current_user: User,
        upload_file: UploadFile,
    ) -> MessageAttachment:
        """Validate, store attachment, and persist metadata transactionally with atomic cleanup."""
        conv = self.repo.get_conversation_by_id(conversation_id)
        if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation thread not found",
            )

        message = self.repo.get_message_by_id(message_id)
        if not message or message.conversation_id != conversation_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found in this conversation",
            )
        if message.sender_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot attach files to messages sent by another user",
            )

        file_uri, mime_type, file_size, attachment_type = self.storage.save_upload(upload_file)

        try:
            attachment = self.repo.create_attachment(
                message_id=message_id,
                file_uri=file_uri,
                file_name=upload_file.filename or "attachment",
                file_mime_type=mime_type,
                file_size_bytes=file_size,
                attachment_type=attachment_type,
            )
            self.db.commit()
            return attachment
        except Exception:
            self.db.rollback()
            # Clean up stored file to prevent orphaned storage accumulation
            self.storage.delete_file(file_uri)
            raise

    def send_message_with_attachment(
        self,
        conversation_id: uuid.UUID,
        current_user: User,
        content: str,
        upload_file: UploadFile,
        order_id: Optional[uuid.UUID] = None,
    ) -> Tuple[Message, MessageAttachment]:
        """Convenience method to persist a message and its initial attachment in one transaction."""
        conv = self.repo.get_conversation_by_id(conversation_id)
        if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation thread not found",
            )

        file_uri, mime_type, file_size, attachment_type = self.storage.save_upload(upload_file)

        try:
            msg = self.repo.create_message(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                content=content or f"Shared {attachment_type}: {upload_file.filename}",
                message_type=MESSAGE_TYPE_TEXT,
                order_id=order_id,
                delivery_status=MESSAGE_STATUS_SENT,
            )
            attachment = self.repo.create_attachment(
                message_id=msg.id,
                file_uri=file_uri,
                file_name=upload_file.filename or "attachment",
                file_mime_type=mime_type,
                file_size_bytes=file_size,
                attachment_type=attachment_type,
            )
            self.db.commit()
            return msg, attachment
        except Exception:
            self.db.rollback()
            self.storage.delete_file(file_uri)
            raise

    def get_attachment_download_path(self, attachment_id: uuid.UUID, current_user: User) -> Tuple[Path, str, str]:
        """Verify participant authorization and resolve filesystem path for attachment retrieval."""
        attachment = self.repo.get_attachment_by_id(attachment_id)
        if not attachment or not attachment.message or not attachment.message.conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment not found",
            )

        conv = attachment.message.conversation
        if current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attachment not found or user is not authorized",
            )

        path = self.storage.get_file_path(attachment.file_uri)
        return path, attachment.file_name, attachment.file_mime_type

    # -------------------------------------------------------------------------
    # M5-07: Contact Information Sharing Consent Workflow
    # -------------------------------------------------------------------------

    def request_contact_sharing(
        self,
        conversation_id: uuid.UUID,
        current_user: User,
        notes: Optional[str] = None,
    ) -> ContactShareRequest:
        """Create a contact sharing consent request for the counterparty."""
        # Row-level lock on conversation thread to serialize concurrent requests
        conv = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .with_for_update()
            .first()
        )
        if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation thread not found",
            )

        recipient_id = conv.buyer_id if current_user.id == conv.farmer_id else conv.farmer_id

        # Check for existing pending request in thread
        active = self.repo.get_active_contact_share_request(conversation_id)
        if active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An active pending contact sharing request already exists for this conversation",
            )

        # Check if consent is already mutually granted
        if self._has_contact_sharing_consent(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contact sharing has already been consented to and enabled for this conversation",
            )

        try:
            req = self.repo.create_contact_share_request(
                conversation_id=conversation_id,
                requester_id=current_user.id,
                recipient_id=recipient_id,
                notes=notes,
            )

            # Post an in-thread notification message
            self.repo.create_message(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                content="[System] Requested mutual contact information sharing.",
                message_type=MESSAGE_TYPE_CONTACT_REQUEST,
            )

            self.db.commit()
            return req
        except Exception:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An active pending contact sharing request already exists for this conversation",
            )

    def respond_to_contact_sharing(
        self,
        request_id: uuid.UUID,
        current_user: User,
        approve: bool,
    ) -> ContactShareRequest:
        """Approve or reject a contact sharing request."""
        req = self.repo.get_contact_share_request_by_id(request_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contact share request not found",
            )

        # Only intended recipient can respond (requester cannot self-approve)
        if req.recipient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the designated recipient may approve or reject a contact share request",
            )

        if req.status != CONTACT_REQUEST_STATUS_PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot respond to request that is already '{req.status}'",
            )

        now_utc = datetime.now(timezone.utc)
        new_status = CONTACT_REQUEST_STATUS_APPROVED if approve else CONTACT_REQUEST_STATUS_REJECTED
        req = self.repo.update_contact_share_request_status(req, new_status, now_utc)

        if approve:
            # Grant mutual consent
            self.repo.update_participant_contact_sharing(req.conversation_id, req.requester_id, True)
            self.repo.update_participant_contact_sharing(req.conversation_id, req.recipient_id, True)
            sys_msg = "[System] Mutual contact information sharing request was approved. Contact details are now visible."
        else:
            sys_msg = "[System] Contact information sharing request was declined."

        self.repo.create_message(
            conversation_id=req.conversation_id,
            sender_id=current_user.id,
            content=sys_msg,
            message_type=MESSAGE_TYPE_SYSTEM,
        )
        self.db.commit()
        return req

    def get_contact_details(self, conversation_id: uuid.UUID, current_user: User) -> Dict[str, Any]:
        """Disclose counterparty contact details only after mutual consent has been granted."""
        conv = self.repo.get_conversation_by_id(conversation_id)
        if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation thread not found",
            )

        if not self._has_contact_sharing_consent(conversation_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contact information sharing has not been mutually consented to in this conversation",
            )

        other_user = conv.buyer if current_user.id == conv.farmer_id else conv.farmer
        return self._format_user_info(other_user, disclose_contact=True)

    # -------------------------------------------------------------------------
    # M5-08: Message Status Tracking
    # -------------------------------------------------------------------------

    def mark_conversation_read(self, conversation_id: uuid.UUID, current_user: User) -> int:
        """Mark all unread counterparty messages as read."""
        conv = self.repo.get_conversation_by_id(conversation_id)
        if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation thread not found",
            )

        # Mark messages read; repository excludes current_user's own messages
        count = self.repo.mark_messages_read(conversation_id, current_user.id)
        self.db.commit()
        return count

    def get_unread_count(self, conversation_id: uuid.UUID, current_user: User) -> int:
        """Return count of unread messages for current user in thread."""
        conv = self.repo.get_conversation_by_id(conversation_id)
        if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation thread not found",
            )
        return self.repo.count_unread_messages(conversation_id, current_user.id)

    # -------------------------------------------------------------------------
    # Helper / Privacy formatting methods
    # -------------------------------------------------------------------------

    def _has_contact_sharing_consent(self, conversation_id: uuid.UUID) -> bool:
        """Verify whether mutual contact sharing consent exists in this conversation."""
        approved_request = (
            self.db.query(ContactShareRequest)
            .filter(
                ContactShareRequest.conversation_id == conversation_id,
                ContactShareRequest.status == CONTACT_REQUEST_STATUS_APPROVED,
            )
            .first()
        )
        if approved_request:
            return True

        participants = (
            self.db.query(ConversationParticipant)
            .filter(ConversationParticipant.conversation_id == conversation_id)
            .all()
        )
        if len(participants) == 2 and all(p.share_contact_details for p in participants):
            return True
        return False

    def _format_user_info(self, user: User, disclose_contact: bool = False) -> Dict[str, Any]:
        """Format participant details, disclosing email and phone strictly when consented."""
        name = "Unknown"
        entity_name = None
        if user.role == "farmer" and user.farmer_profile:
            name = user.farmer_profile.full_name
            entity_name = user.farmer_profile.farm_name
        elif user.role == "buyer" and user.buyer_profile:
            name = user.buyer_profile.contact_person_name
            entity_name = user.buyer_profile.business_name

        data: Dict[str, Any] = {
            "id": user.id,
            "role": user.role,
            "verification_status": user.verification_status,
            "name": name,
            "entity_name": entity_name,
            "email": user.email if disclose_contact else None,
            "phone_number": user.phone_number if disclose_contact else None,
        }
        return data
