"""
Creates Gmail drafts from generated reply text.
Drafts are threaded properly (appear as a reply in the original
conversation, not a standalone new email) and are NEVER auto-sent —
the user reviews and sends manually from Gmail.
"""

import base64
from email.mime.text import MIMEText
from src.auth.gmail_auth import get_gmail_service


def create_draft_reply(email: dict) -> dict:
    """
    Creates a Gmail draft reply for a single email.
    email dict must contain: id, thread_id, sender, subject, draft
    """
    service = get_gmail_service()

    # Build a proper reply subject (Re: prefix, avoid double "Re: Re:")
    subject = email["subject"]
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    message = MIMEText(email["draft"])
    message["to"] = _extract_email_address(email["sender"])
    message["subject"] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

    draft = service.users().drafts().create(
        userId="me",
        body={
            "message": {
                "raw": raw_message,
                "threadId": email["thread_id"]  # keeps it in the same conversation
            }
        }
    ).execute()

    return draft


def _extract_email_address(sender_field: str) -> str:
    """
    Extracts just the email address from a 'From' header like
    'John Doe <john@example.com>' -> 'john@example.com'
    """
    if "<" in sender_field and ">" in sender_field:
        return sender_field.split("<")[1].split(">")[0].strip()
    return sender_field.strip()