"""FastAPI REST router for Module 5 chat, messaging, attachments, and contact sharing."""

import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.chat.schemas import (
    ContactDetailsResponse,
    ContactShareRequestCreate,
    ContactShareRequestResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    MessageAttachmentResponse,
    MessageCreate,
    MessageResponse,
    ReadStatusResponse,
    UnreadCountResponse,
)
from app.chat.service import ChatService
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter(tags=["chat"])


# ---------------------------------------------------------------------------
# Conversation Endpoints (M5-01, M5-02)
# ---------------------------------------------------------------------------

@router.post(
    "/conversations",
    response_model=ConversationDetailResponse,
    summary="Create or retrieve a conversation thread",
    description="Initiate a conversation or retrieve an existing canonical thread between counterparts.",
)
def create_conversation(
    payload: ConversationCreate,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    """Create or retrieve a direct conversation thread."""
    service = ChatService(db)
    conv, created = service.create_or_get_conversation(
        current_user=current_user,
        target_user_id=payload.target_user_id,
        listing_id=payload.listing_id,
        requirement_id=payload.requirement_id,
        order_id=payload.order_id,
        offer_id=payload.offer_id,
    )
    if created:
        response.status_code = status.HTTP_201_CREATED
    else:
        response.status_code = status.HTTP_200_OK

    return ConversationDetailResponse.model_validate(service.get_conversation_details(conv.id, current_user))


@router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations for current user",
    description="Retrieve all conversation threads belonging to the authenticated user.",
)
def list_conversations(
    context_type: Optional[str] = Query(None, description="Filter by initial context type"),
    order_id: Optional[uuid.UUID] = Query(None, description="Filter by linked order UUID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    """List authenticated user's conversations with unread counts."""
    service = ChatService(db)
    items, total = service.list_conversations(
        current_user=current_user,
        context_type=context_type,
        order_id=order_id,
        limit=limit,
        offset=offset,
    )
    return ConversationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation details",
    description="Retrieve full conversation details, participant info, and contact consent state.",
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    """Retrieve individual conversation details."""
    service = ChatService(db)
    details = service.get_conversation_details(conversation_id, current_user)
    return ConversationDetailResponse.model_validate(details)


# ---------------------------------------------------------------------------
# Messaging Endpoints (M5-03, M5-04)
# ---------------------------------------------------------------------------

@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a text message",
    description="Send a text message in an authorized conversation thread.",
)
def send_message(
    conversation_id: uuid.UUID,
    payload: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Send text message within thread."""
    service = ChatService(db)
    msg = service.send_message(
        conversation_id=conversation_id,
        current_user=current_user,
        content=payload.content,
        order_id=payload.order_id,
    )
    return MessageResponse.model_validate(msg)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=List[MessageResponse],
    summary="Get conversation message history",
    description="Retrieve ordered message history with cursor-based pagination.",
)
def get_message_history(
    conversation_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[uuid.UUID] = Query(None, description="Cursor for older messages"),
    after_id: Optional[uuid.UUID] = Query(None, description="Cursor for newer messages"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[MessageResponse]:
    """Retrieve message history."""
    service = ChatService(db)
    messages = service.list_messages(
        conversation_id=conversation_id,
        current_user=current_user,
        limit=limit,
        before_id=before_id,
        after_id=after_id,
        order=order,
    )
    return [MessageResponse.model_validate(m) for m in messages]


# ---------------------------------------------------------------------------
# Attachment Endpoints (M5-05, M5-06, M5-11)
# ---------------------------------------------------------------------------

@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/attachments",
    response_model=MessageAttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload attachment for an existing message",
    description="Attach an image or document to an authorized message.",
)
def upload_attachment(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageAttachmentResponse:
    """Upload attachment for an existing message."""
    service = ChatService(db)
    attachment = service.upload_attachment_for_message(
        conversation_id=conversation_id,
        message_id=message_id,
        current_user=current_user,
        upload_file=file,
    )
    return MessageAttachmentResponse.model_validate(attachment)


@router.post(
    "/conversations/{conversation_id}/messages/with-attachment",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send message with an attachment in a single request",
    description="Convenience endpoint to send a message with an attached file atomically.",
)
def send_message_with_attachment(
    conversation_id: uuid.UUID,
    content: str = Form(...),
    order_id: Optional[uuid.UUID] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Send message and attachment together."""
    service = ChatService(db)
    msg, _ = service.send_message_with_attachment(
        conversation_id=conversation_id,
        current_user=current_user,
        content=content,
        upload_file=file,
        order_id=order_id,
    )
    return MessageResponse.model_validate(msg)


@router.get(
    "/attachments/{attachment_id}",
    summary="Download or view an attachment",
    description="Retrieve a stored chat attachment securely with participant-level authorization.",
)
def download_attachment(
    attachment_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    """Safely stream stored attachment."""
    service = ChatService(db)
    file_path, file_name, mime_type = service.get_attachment_download_path(attachment_id, current_user)
    return FileResponse(
        path=str(file_path),
        filename=file_name,
        media_type=mime_type,
    )


# ---------------------------------------------------------------------------
# Message Status Tracking Endpoints (M5-08)
# ---------------------------------------------------------------------------

@router.post(
    "/conversations/{conversation_id}/read",
    response_model=ReadStatusResponse,
    summary="Mark messages as read",
    description="Mark unread counterparty messages in the conversation as read.",
)
def mark_conversation_read(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ReadStatusResponse:
    """Mark unread messages as read."""
    service = ChatService(db)
    marked_count = service.mark_conversation_read(conversation_id, current_user)
    return ReadStatusResponse(
        conversation_id=conversation_id,
        marked_read_count=marked_count,
    )


@router.get(
    "/conversations/{conversation_id}/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread message count",
    description="Retrieve total unread messages for the authenticated user in this thread.",
)
def get_unread_count(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> UnreadCountResponse:
    """Get unread message count."""
    service = ChatService(db)
    count = service.get_unread_count(conversation_id, current_user)
    return UnreadCountResponse(
        conversation_id=conversation_id,
        unread_count=count,
    )


# ---------------------------------------------------------------------------
# Contact Sharing Consent Endpoints (M5-07)
# ---------------------------------------------------------------------------

@router.post(
    "/conversations/{conversation_id}/contact-requests",
    response_model=ContactShareRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request mutual contact information sharing",
    description="Initiate a consent workflow to exchange phone numbers and email addresses.",
)
def request_contact_sharing(
    conversation_id: uuid.UUID,
    payload: ContactShareRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ContactShareRequestResponse:
    """Initiate contact sharing consent request."""
    service = ChatService(db)
    req = service.request_contact_sharing(
        conversation_id=conversation_id,
        current_user=current_user,
        notes=payload.notes,
    )
    return ContactShareRequestResponse.model_validate(req)


@router.get(
    "/conversations/{conversation_id}/contact-requests",
    response_model=List[ContactShareRequestResponse],
    summary="List contact sharing requests for conversation",
    description="List all historical and active contact sharing requests in this conversation.",
)
def list_contact_requests(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> List[ContactShareRequestResponse]:
    """List contact requests for conversation."""
    service = ChatService(db)
    # Validate participation
    conv = service.repo.get_conversation_by_id(conversation_id)
    if not conv or current_user.id not in (conv.farmer_id, conv.buyer_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation thread not found",
        )
    requests = service.repo.list_contact_share_requests(conversation_id)
    return [ContactShareRequestResponse.model_validate(r) for r in requests]


@router.post(
    "/contact-requests/{request_id}/approve",
    response_model=ContactShareRequestResponse,
    summary="Approve contact information sharing",
    description="Approve a received contact sharing request to grant mutual consent.",
)
def approve_contact_sharing(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ContactShareRequestResponse:
    """Approve contact sharing request."""
    service = ChatService(db)
    req = service.respond_to_contact_sharing(request_id, current_user, approve=True)
    return ContactShareRequestResponse.model_validate(req)


@router.post(
    "/contact-requests/{request_id}/reject",
    response_model=ContactShareRequestResponse,
    summary="Reject contact information sharing",
    description="Decline a received contact sharing request.",
)
def reject_contact_sharing(
    request_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ContactShareRequestResponse:
    """Reject contact sharing request."""
    service = ChatService(db)
    req = service.respond_to_contact_sharing(request_id, current_user, approve=False)
    return ContactShareRequestResponse.model_validate(req)


@router.get(
    "/conversations/{conversation_id}/contacts",
    response_model=ContactDetailsResponse,
    summary="Get counterparty contact details",
    description="Retrieve disclosed phone and email after mutual consent is established.",
)
def get_contact_details(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> ContactDetailsResponse:
    """Retrieve consented contact details."""
    service = ChatService(db)
    details = service.get_contact_details(conversation_id, current_user)
    return ContactDetailsResponse.model_validate(details)
