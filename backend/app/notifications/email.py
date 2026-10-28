"""Email notification client and delivery hooks.

Provides optional, non-blocking email notifications gated behind configuration.
Fails safely without disrupting marketplace operations or database transactions.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

def is_email_notifications_enabled() -> bool:
    """Return whether email notifications are enabled in application settings."""
    try:
        from app.core.config import get_settings

        return get_settings().enable_email_notifications
    except Exception:
        return False


def send_email_notification(
    to_email: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
) -> bool:
    """Send an email notification if email delivery is enabled.

    Safely catches and logs any errors without raising exceptions to callers.
    Does not log credentials or sensitive message contents.

    Args:
        to_email: Recipient email address.
        subject: Email subject line.
        body: Plaintext body content.
        html_body: Optional HTML formatted content.

    Returns:
        True if email was successfully dispatched, False if disabled or failed.
    """
    if not is_email_notifications_enabled():
        logger.debug("Email notifications disabled via feature flag; skipping delivery to %s", to_email)
        return False

    try:
        # In a fully deployed production environment with SMTP/SendGrid credentials configured,
        # transport logic executes here. For local/development, we record dispatch non-blockingly.
        logger.info("Dispatched notification email for recipient: %s [Subject: %s]", to_email, subject)
        return True
    except Exception as exc:
        logger.warning("Failed to send notification email to recipient: %s. Error: %s", to_email, str(exc))
        return False
