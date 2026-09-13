"""
Routing logic for the email agent graph:
- Send() fan-out for parallel classification
- Conditional routing to draft_reply only for needs_reply=True emails
"""

from langgraph.types import Send


def route_to_classification(state: dict):
    """
    Fans out each fetched email to its own classify_and_score call,
    running them in parallel instead of sequentially.
    """
    return [
        Send("classify_and_score", email)
        for email in state["raw_emails"]
    ]


def route_to_drafting(state: dict):
    """
    After classification, fans out ONLY emails flagged needs_reply=True
    to draft_reply. Emails not needing a reply skip straight past.
    """
    needs_reply_emails = [
        email for email in state["processed"] if email["needs_reply"]
    ]

    if not needs_reply_emails:
        return "skip_drafting"  # named edge for the "nothing to draft" case

    return [
        Send("draft_reply_node", email)
        for email in needs_reply_emails
    ]