"""
Tracks which Gmail message IDs have already been processed,
so re-runs don't reclassify or re-draft the same emails.
Backed by Supabase (Postgres) — persists across GitHub Actions'
fresh-container-per-run model with zero git hackiness.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Lazily creates and reuses a single Supabase client instance."""
    global _supabase_client
    if _supabase_client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _supabase_client = create_client(url, key)
    return _supabase_client


def get_processed_ids() -> set[str]:
    """
    Returns the set of all Gmail message IDs already processed.
    Used to filter out emails we've already classified/drafted.
    """
    client = get_supabase_client()
    response = client.table("processed_emails").select("id").execute()
    return {row["id"] for row in response.data}


def mark_as_processed(email_ids: list[str]) -> None:
    """
    Records a batch of email IDs as processed.
    Uses upsert so re-running on an already-processed ID doesn't error.
    """
    if not email_ids:
        return

    client = get_supabase_client()
    rows = [{"id": eid} for eid in email_ids]
    client.table("processed_emails").upsert(rows).execute()


def filter_unprocessed(emails: list[dict]) -> list[dict]:
    """
    Given a list of email dicts (each with an 'id' key),
    returns only the ones NOT already in processed_emails.
    """
    processed_ids = get_processed_ids()
    return [e for e in emails if e["id"] not in processed_ids]