"""Service layer for notifications and operational alerts.

Implements business logic, scoped retrieval, read acknowledgement,
and event-driven notification dispatching across the AgriDirect platform.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import (
    NOTIFICATION_REF_LISTING,
    NOTIFICATION_REF_OFFER,
    NOTIFICATION_REF_ORDER,
    NOTIFICATION_REF_VERIFICATION,
    Notification,
)
from app.models.user import User
from app.notifications.email import send_email_notification
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import (
    NotificationCreate,
    NotificationListResponse,
    NotificationRead,
)

# Canonical domain event names
EVENT_VERIFICATION_STATUS_CHANGED = "verification_status_change"
EVENT_OFFER_RECEIVED = "offer_received"
EVENT_COUNTER_OFFER_RECEIVED = "counter_offer_received"
EVENT_OFFER_ACCEPTED = "offer_accepted"
EVENT_OFFER_REJECTED = "offer_rejected"
EVENT_ORDER_STATUS_CHANGED = "order_status_change"
EVENT_AMENDMENT_PROPOSED = "amendment_requested"
EVENT_AMENDMENT_CONFIRMED = "amendment_confirmed"
EVENT_AMENDMENT_REJECTED = "amendment_rejected"
EVENT_PAYMENT_RECORDED = "payment_recorded"
EVENT_PAYMENT_ACKNOWLEDGED = "payment_acknowledged"


class NotificationService:
    """Orchestrates notification business operations, validations, and domain events."""

    def __init__(
        self,
        db: Session,
        repository: Optional[NotificationRepository] = None,
    ) -> None:
        """Initialize service with database session and repository.

        Args:
            db: Active database session.
            repository: Optional repository instance (constructed if None).
        """
        self.db = db
        self.repo = repository or NotificationRepository(db)

    def create_notification(
        self,
        user_id: uuid.UUID,
        event_type: str,
        title: str,
        body: str,
        reference_type: Optional[str] = None,
        reference_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        """Create and persist an in-app notification.

        Args:
            user_id: Recipient user ID.
            event_type: Notification category/event key.
            title: Headline summary.
            body: Full message narrative.
            reference_type: Context entity type (order, offer, listing, verification).
            reference_id: Primary key of context entity.

        Returns:
            Committed Notification model instance.

        Raises:
            ValueError: If input validation fails or user does not exist.
        """
        if not title or not title.strip():
            raise ValueError("Notification title cannot be empty")
        if not body or not body.strip():
            raise ValueError("Notification body cannot be empty")
        if not event_type or not event_type.strip():
            raise ValueError("Notification event_type cannot be empty")

        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} does not exist")

        notification_in = NotificationCreate(
            user_id=user_id,
            event_type=event_type.strip(),
            title=title.strip(),
            body=body.strip(),
            reference_type=reference_type.strip() if reference_type else None,
            reference_id=reference_id,
        )

        notification = self.repo.create(notification_in)
        self.db.commit()
        self.db.refresh(notification)

        # Dispatch optional email if user has email and email service is enabled
        if user.email:
            send_email_notification(
                to_email=user.email,
                subject=f"[AgriDirect] {notification.title}",
                body=notification.body,
            )

        return notification

    def list_user_notifications(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> NotificationListResponse:
        """Retrieve paginated notifications scoped to the authenticated user.

        Args:
            user_id: The authenticated user's ID.
            page: 1-indexed page number.
            page_size: Number of items per page.
            unread_only: Filter only unread items when True.

        Returns:
            NotificationListResponse containing items, counts, and pagination metadata.
        """
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 20
        if page_size > 100:
            page_size = 100

        skip = (page - 1) * page_size
        items = self.repo.list_for_user(
            user_id=user_id,
            skip=skip,
            limit=page_size,
            unread_only=unread_only,
        )
        total = self.repo.count_for_user(user_id=user_id, unread_only=unread_only)
        unread_count = self.repo.count_unread_for_user(user_id=user_id)

        items_read = [NotificationRead.model_validate(item) for item in items]
        return NotificationListResponse.create(
            items=items_read,
            total=total,
            unread_count=unread_count,
            page=page,
            page_size=page_size,
        )

    def mark_as_read(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification:
        """Mark a notification as read with ownership enforcement.

        Args:
            notification_id: Primary key of notification to mark read.
            user_id: Authenticated user ID.

        Returns:
            Updated Notification instance.

        Raises:
            HTTPException: 404 if notification doesn't exist.
            HTTPException: 403 if notification belongs to another user.
        """
        notification = self.repo.get_by_id_and_user(
            notification_id=notification_id,
            user_id=user_id,
        )
        if notification is None:
            # Check if it exists for another user to return 403
            other = self.repo.get_by_id(notification_id)
            if other is not None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Forbidden: You do not have permission to access this notification",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        now_utc = datetime.now(timezone.utc)
        self.repo.mark_as_read(notification, read_time=now_utc)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    # -----------------------------------------------------------------------
    # Domain Event Trigger Handlers
    # -----------------------------------------------------------------------

    def notify_verification_status_change(
        self,
        user_id: uuid.UUID,
        new_status: str,
        admin_notes: Optional[str] = None,
    ) -> Notification:
        """Notify user when administrative verification status changes."""
        title = "Account Verification Update"
        if new_status == "verified":
            body = "Congratulations! Your account verification has been approved. You now have full trading access."
        elif new_status == "rejected":
            reason = f" Reason: {admin_notes}" if admin_notes else ""
            body = f"Your verification submission was not approved.{reason} Please review and resubmit."
        else:
            body = f"Your account verification status is now: {new_status}."

        return self.create_notification(
            user_id=user_id,
            event_type=EVENT_VERIFICATION_STATUS_CHANGED,
            title=title,
            body=body,
            reference_type=NOTIFICATION_REF_VERIFICATION,
        )

    def notify_offer_received(
        self,
        recipient_id: uuid.UUID,
        offer_id: uuid.UUID,
        offer_number: str,
        sender_label: str = "A counterparty",
    ) -> Notification:
        """Notify user of a newly received negotiation offer."""
        return self.create_notification(
            user_id=recipient_id,
            event_type=EVENT_OFFER_RECEIVED,
            title="New Offer Received",
            body=f"{sender_label} submitted a new offer {offer_number}. Review terms and respond.",
            reference_type=NOTIFICATION_REF_OFFER,
            reference_id=offer_id,
        )

    def notify_counter_offer_received(
        self,
        recipient_id: uuid.UUID,
        offer_id: uuid.UUID,
        offer_number: str,
    ) -> Notification:
        """Notify user of a counter-offer proposal."""
        return self.create_notification(
            user_id=recipient_id,
            event_type=EVENT_COUNTER_OFFER_RECEIVED,
            title="Counter-Offer Received",
            body=f"A counter-offer {offer_number} has been proposed. Review the updated terms.",
            reference_type=NOTIFICATION_REF_OFFER,
            reference_id=offer_id,
        )

    def notify_offer_accepted(
        self,
        sender_id: uuid.UUID,
        offer_id: uuid.UUID,
        offer_number: str,
    ) -> Notification:
        """Notify offer sender that their offer was accepted."""
        return self.create_notification(
            user_id=sender_id,
            event_type=EVENT_OFFER_ACCEPTED,
            title="Offer Accepted",
            body=f"Your offer {offer_number} has been accepted. A formal order has been created.",
            reference_type=NOTIFICATION_REF_OFFER,
            reference_id=offer_id,
        )

    def notify_offer_rejected(
        self,
        sender_id: uuid.UUID,
        offer_id: uuid.UUID,
        offer_number: str,
    ) -> Notification:
        """Notify offer sender that their offer was rejected."""
        return self.create_notification(
            user_id=sender_id,
            event_type=EVENT_OFFER_REJECTED,
            title="Offer Declined",
            body=f"Your offer {offer_number} was declined by the counterparty.",
            reference_type=NOTIFICATION_REF_OFFER,
            reference_id=offer_id,
        )

    def notify_order_status_change(
        self,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
        order_number: str,
        new_status: str,
    ) -> Notification:
        """Notify buyer or farmer when order status changes."""
        return self.create_notification(
            user_id=user_id,
            event_type=EVENT_ORDER_STATUS_CHANGED,
            title=f"Order {order_number} Update",
            body=f"Order {order_number} status is now: {new_status}.",
            reference_type=NOTIFICATION_REF_ORDER,
            reference_id=order_id,
        )

    def notify_amendment_proposed(
        self,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
        amendment_id: uuid.UUID,
        order_number: str,
        amendment_type: str,
    ) -> Notification:
        """Notify counterparty that an order amendment has been requested."""
        return self.create_notification(
            user_id=user_id,
            event_type=EVENT_AMENDMENT_PROPOSED,
            title=f"Order {order_number} Amendment Requested",
            body=f"An amendment regarding {amendment_type} was proposed for Order {order_number}. Your confirmation is required.",
            reference_type=NOTIFICATION_REF_ORDER,
            reference_id=order_id,
        )

    def notify_payment_recorded(
        self,
        farmer_id: uuid.UUID,
        order_id: uuid.UUID,
        payment_id: uuid.UUID,
        order_number: str,
        amount_display: str,
    ) -> Notification:
        """Notify farmer that buyer recorded an off-platform payment."""
        return self.create_notification(
            user_id=farmer_id,
            event_type=EVENT_PAYMENT_RECORDED,
            title=f"Payment Recorded for Order {order_number}",
            body=f"Buyer recorded a payment of {amount_display} for Order {order_number}. Please verify and acknowledge receipt.",
            reference_type=NOTIFICATION_REF_ORDER,
            reference_id=order_id,
        )

    def notify_payment_acknowledged(
        self,
        buyer_id: uuid.UUID,
        order_id: uuid.UUID,
        payment_id: uuid.UUID,
        order_number: str,
    ) -> Notification:
        """Notify buyer that farmer acknowledged receipt of payment."""
        return self.create_notification(
            user_id=buyer_id,
            event_type=EVENT_PAYMENT_ACKNOWLEDGED,
            title=f"Payment Acknowledged for Order {order_number}",
            body=f"Farmer acknowledged receipt of payment for Order {order_number}.",
            reference_type=NOTIFICATION_REF_ORDER,
            reference_id=order_id,
        )
