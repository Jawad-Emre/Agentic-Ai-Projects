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

def route_to_agent(state: dict):
    """After labels are applied, fan out each email to the agent loop."""
    return [
        Send("run_agent_for_email", email)
        for email in state["processed"]
        if not email.get("classification_failed", False)
    ]
