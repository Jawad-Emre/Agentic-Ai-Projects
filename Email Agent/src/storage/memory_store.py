"""Best-effort sender memory stored in Supabase."""

import logging

from src.storage.processed_store import get_supabase_client


logger = logging.getLogger(__name__)


def get_sender_memory(sender: str) -> dict | None:
    """Return the latest memory for a sender, if available."""
    try:
        response = (
            get_supabase_client()
            .table("agent_memory")
            .select("sender, labels, last_action, importance_score, updated_at")
            .eq("sender", sender)
            .maybe_single()
            .execute()
        )
        return response.data
    except Exception as error:
        logger.warning("Sender memory unavailable for %s: %s", sender, error)
        return None


def record_sender_memory(
    sender: str,
    labels: list[str],
    importance_score: float,
    action: str,
    success: bool,
) -> None:
    """Store the latest sender behavior without blocking email handling."""
    try:
        (
            get_supabase_client()
            .table("agent_memory")
            .upsert({
                "sender": sender,
                "labels": labels,
                "importance_score": importance_score,
                "last_action": action,
                "last_success": success,
            }, on_conflict="sender")
            .execute()
        )
    except Exception as error:
        logger.warning("Could not save sender memory for %s: %s", sender, error)