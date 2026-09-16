"""Apply classification labels to Gmail messages."""

import logging

from src.auth.gmail_auth import get_gmail_service

# Cache: label name -> Gmail label ID, populated once per run
_label_id_cache: dict[str, str] = {}
_SYSTEM_LABEL_IDS = {"STARRED", "IMPORTANT", "INBOX"}
logger = logging.getLogger(__name__)


def get_or_create_label(service, label_name: str) -> str:
    """
    Returns the Gmail label ID for a given name, creating it if it
    doesn't exist yet. Caches results to avoid repeated API calls
    for the same label within one run.
    """
    if label_name in _label_id_cache:
        return _label_id_cache[label_name]

    # Check if label already exists
    existing = service.users().labels().list(userId='me').execute()
    for label in existing.get('labels', []):
        if label['name'] == label_name:
            _label_id_cache[label_name] = label['id']
            return label['id']

    # Doesn't exist — create it
    new_label = service.users().labels().create(
        userId='me',
        body={
            'name': label_name,
            'labelListVisibility': 'labelShow',
            'messageListVisibility': 'show'
        }
    ).execute()

    _label_id_cache[label_name] = new_label['id']
    return new_label['id']


def apply_labels_to_email(email_id: str, label_names: list[str]) -> None:
    """
    Applies one or more labels to a single Gmail message.
    """
    service = get_gmail_service()
    label_ids = [
        name if name in _SYSTEM_LABEL_IDS else get_or_create_label(service, name)
        for name in label_names
    ]

    service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'addLabelIds': label_ids}
    ).execute()


def archive_email(email_id: str) -> None:
    """Archives a message by removing Gmail's INBOX system label."""
    service = get_gmail_service()
    service.users().messages().modify(
        userId='me',
        id=email_id,
        body={'removeLabelIds': ['INBOX']}
    ).execute()


def apply_labels_batch(classified_emails: list[dict]) -> list[str]:
    """
    Applies labels to a batch of already-classified emails.
    Each dict must have 'id' and 'labels' keys.
    """
    failures = []
    for email in classified_emails:
        try:
            apply_labels_to_email(email['id'], email['labels'])
            logger.info("Labeled '%s' -> %s", email['subject'][:50], email['labels'])
        except Exception as error:
            logger.exception("Labeling failed for %s", email['id'])
            failures.append(email['id'])
    return failures