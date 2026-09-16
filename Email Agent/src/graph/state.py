"""
State schemas for the email agent graph.
"""

from typing import TypedDict, Annotated
from operator import add
from langgraph.graph.message import add_messages


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
    messages: Annotated[list, add_messages]
    classification_failed: bool


class GraphState(TypedDict):
    raw_emails: list[dict]
    processed: Annotated[list[EmailState], add]
    handled: Annotated[list[dict], add]
    label_failed_ids: Annotated[list[str], add]