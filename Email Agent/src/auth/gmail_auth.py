"""
Single source of truth for getting an authenticated Gmail API client.
Loads secrets from environment variables (populated via .env locally,
or via GitHub Secrets in production).
"""

import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()  # no-op in GitHub Actions where env vars are injected directly

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]


def get_gmail_service():
    """
    Rebuilds credentials from refresh token every call.
    No token file needed, no browser login needed — works identically
    locally and in a fresh GitHub Actions container.
    """
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GMAIL_REFRESH_TOKEN"],
        client_id=os.environ["GMAIL_CLIENT_ID"],
        client_secret=os.environ["GMAIL_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES
    )

    service = build('gmail', 'v1', credentials=creds)
    return service