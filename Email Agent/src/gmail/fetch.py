"""
Fetches unread emails from Gmail and parses them into clean,
structured dicts — ready for classification.
"""

import base64
from email import message_from_bytes
from src.auth.gmail_auth import get_gmail_service
from email.header import decode_header, make_header

from bs4 import BeautifulSoup

def fetch_unread_emails(max_results: int = 10) -> list[dict]:
    """
    Fetches up to `max_results` unread emails.
    Returns a list of dicts: {id, thread_id, sender, subject, body}
    """
    service = get_gmail_service()

    results = service.users().messages().list(
        userId='me',
        q='is:unread',
        maxResults=max_results
    ).execute()

    messages = results.get('messages', [])

    emails = []
    for msg in messages:
        full_msg = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='raw'  # raw = full MIME, needed to handle multipart bodies
        ).execute()

        parsed = _parse_raw_message(full_msg)
        emails.append(parsed)

    return emails


def _parse_raw_message(full_msg: dict) -> dict:
    raw_data = base64.urlsafe_b64decode(full_msg['raw'])
    mime_msg = message_from_bytes(raw_data)

    sender = _decode_mime_header(mime_msg.get('From', 'Unknown'))
    subject = _decode_mime_header(mime_msg.get('Subject', '(No Subject)'))
    body = _extract_body(mime_msg)

    return {
        "id": full_msg['id'],
        "thread_id": full_msg['threadId'],
        "sender": sender,
        "subject": subject,
        "body": body.strip()
    }


def _decode_mime_header(header_value: str) -> str:
    """
    Decodes RFC 2047 encoded headers (e.g., '=?UTF-8?Q?...?=')
    into normal readable text.
    """
    if not header_value:
        return ""
    try:
        return str(make_header(decode_header(header_value)))
    except Exception:
        return header_value  # fallback: return as-is if decoding fails


def _extract_body(mime_msg) -> str:
    """
    Walks a MIME message and extracts plain text.
    Falls back to stripping HTML tags if only an HTML part exists.
    Also strips HTML from "plain text" parts that are actually mislabeled HTML.
    """
    if mime_msg.is_multipart():
        for part in mime_msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get('Content-Disposition', ''))
            if content_type == 'text/plain' and 'attachment' not in disposition:
                payload = part.get_payload(decode=True)
                if payload:
                    text = payload.decode(errors='ignore')
                    if '<' in text and '>' in text:
                        return _strip_html(text)
                    return _normalize_text(text)

        for part in mime_msg.walk():
            if part.get_content_type() == 'text/html':
                payload = part.get_payload(decode=True)
                if payload:
                    return _strip_html(payload.decode(errors='ignore'))

        return "(No readable body found)"
    else:
        payload = mime_msg.get_payload(decode=True)
        if payload:
            text = payload.decode(errors='ignore')
            if '<' in text and '>' in text:
                return _strip_html(text)
            return _normalize_text(text)
        return "(No readable body found)"


def _normalize_text(text: str) -> str:
    """
    Cleans up extracted email text for cases where plain-text email clients
    merge a date header with the next sentence, e.g. "30 AugustBased on...".
    """
    import re

    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(
        r'(?i)(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?=[A-Z])',
        r'\1 ',
        text,
    )
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n\s*\n+', '\n', text)
    text = re.sub(r' *\n *', '\n', text)
    return text.strip()


def _strip_html(html: str) -> str:
    """
    Properly strips HTML using a real parser.
    Explicitly inserts newlines at block-level boundaries to prevent
    run-on text where tags don't naturally separate content.
    """
    soup = BeautifulSoup(html, 'html.parser')

    # Force line breaks before block-level elements so text doesn't merge
    for tag in soup.find_all(['div', 'p', 'br', 'li', 'tr', 'h1', 'h2', 'h3']):
        tag.insert_before('\n')
        tag.insert_after('\n')

    text = soup.get_text(separator=' ', strip=True)
    text = _normalize_text(text)
    return text.strip()