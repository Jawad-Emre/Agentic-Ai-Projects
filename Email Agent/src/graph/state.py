"""
State schemas for the email agent graph.
"""

from typing import TypedDict, Annotated
from operator import add


class EmailState(TypedDict):
    id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    labels: list[str]
    importance_score: float
    needs_reply: bool
    reasoning: str


class GraphState(TypedDict):
    raw_emails: list[dict]
    processed: Annotated[list[EmailState], add]  # merges parallel Send() outputs
    drafted: Annotated[list[dict], add]