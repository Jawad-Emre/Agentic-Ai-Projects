"""Graph nodes for the email agent."""

import logging

from src.llm.client import get_llm, MODEL_FALLBACK_CHAIN
from src.llm.prompts import EmailClassification, CLASSIFICATION_PROMPT_TEMPLATE
from src.graph.state import EmailState

from src.llm.prompts import DRAFT_REPLY_PROMPT_TEMPLATE

from src.gmail.labels import apply_labels_batch, apply_labels_to_email
from src.storage.processed_store import mark_as_processed
from src.gmail.fetch import fetch_unread_emails
from src.storage.processed_store import filter_unprocessed
from src.storage.memory_store import get_sender_memory, record_sender_memory

from langchain_core.messages import SystemMessage, HumanMessage
from src.graph.tools import build_email_tools
from src.llm.prompts import DECISION_SYSTEM_PROMPT


logger = logging.getLogger(__name__)


PRIORITY_LABELS = {
    "Urgent-Reply-Needed",
    "Interview-Invite",
    "Shortlisted",
    "Offer",
    "Finance-Alert",
}
PRIORITY_SCORE_THRESHOLD = 0.8


def is_priority_email(email: dict) -> bool:
    return bool(PRIORITY_LABELS.intersection(email.get("labels", []))) or (
        email.get("importance_score", 0) >= PRIORITY_SCORE_THRESHOLD
    )


def classify_and_score(email: dict) -> dict:
    prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
        sender=email["sender"],
        subject=email["subject"],
        body=email["body"][:3000]
    )

    result = None
    last_error = None

    for model_name in MODEL_FALLBACK_CHAIN:
        try:
            llm = get_llm(model_name=model_name, temperature=0.2)
            structured_llm = llm.with_structured_output(EmailClassification)
            result = structured_llm.invoke(prompt)
            break
        except Exception as e:
            last_error = e
            logger.warning("Classification model %s failed for %s: %s", model_name, email["id"], e)
            continue

    classification_failed = result is None
    if classification_failed:
        logger.error("All classification models failed for %s: %s", email["id"], last_error)
        result = EmailClassification(
            labels=["Other"], importance_score=0.3, needs_reply=False,
            reasoning=f"All models exhausted. Last error: {str(last_error)[:100]}"
        )

    classified: EmailState = {
        **email, "labels": result.labels, "importance_score": result.importance_score,
        "needs_reply": result.needs_reply, "reasoning": result.reasoning,
        "classification_failed": classification_failed,
    }
    return {"processed": [classified]}


def fetch_unread_node(state: dict) -> dict:
    """Fetches unread emails and filters out already-processed ones."""
    emails = fetch_unread_emails()
    new_emails = filter_unprocessed(emails)
    logger.info("Fetched %d unread, %d are new", len(emails), len(new_emails))
    return {"raw_emails": new_emails}


def run_agent_for_email(email: dict) -> dict:
    """
    Full per-email agentic loop, run as a single Send() target:
    seed context -> LLM decides action -> execute the chosen tool.
    Kept as one node because per-email state (messages) doesn't
    survive being split across separate graph nodes in this topology.
    """
    if is_priority_email(email):
        apply_labels_to_email(email["id"], ["Needs-Reply", "IMPORTANT", "STARRED"])
        outcome = {**email, "action": "priority_review", "success": True}
        record_sender_memory(email["sender"], email["labels"], email["importance_score"], outcome["action"], True)
        return {"handled": [outcome]}

    memory = get_sender_memory(email["sender"])
    memory_context = memory or "No previous sender history available."

    prompt = DECISION_SYSTEM_PROMPT.format(
        sender=email["sender"],
        subject=email["subject"],
        body=email["body"][:3000],
        labels=email.get("labels", []),
        importance_score=email.get("importance_score", 0),
        needs_reply=email.get("needs_reply", False),
        sender_memory=memory_context,
    )
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content="Decide which action to take for this email by calling exactly one tool."),
    ]

    tools = build_email_tools(email)
    response = None
    last_error = None

    for model_name in MODEL_FALLBACK_CHAIN:
        try:
            llm = get_llm(model_name=model_name, temperature=0.2)
            llm_with_tools = llm.bind_tools(tools)
            response = llm_with_tools.invoke(messages)
            break
        except Exception as e:
            last_error = e
            logger.warning("Decision model %s failed for %s: %s", model_name, email["id"], e)
            continue

    if response is None or not getattr(response, "tool_calls", None):
        logger.error("No action decided for %s: %s", email["id"], last_error)
        return {"handled": [{
            **email,
            "action": "none",
            "success": False,
            "error": str(last_error or "No tool call returned"),
        }]}

    tool_map = {t.name: t for t in tools}
    try:
        action_taken = "none"
        for call in response.tool_calls:
            tool_fn = tool_map.get(call["name"])
            if tool_fn is None:
                raise RuntimeError(f"Unknown tool returned by model: {call['name']}")
            tool_fn.invoke(call["args"])
            action_taken = call["name"]
        return {"handled": [{**email, "action": action_taken, "success": True}]}
    except Exception as error:
        logger.exception("Action failed for %s", email["id"])
        return {"handled": [{
            **email, "action": "none", "success": False, "error": str(error),
        }]}



def apply_labels_node(state: dict) -> dict:
    """Writes classification labels back to Gmail for all processed emails."""
    failures = apply_labels_batch(
        email for email in state["processed"]
        if not email.get("classification_failed", False)
    )
    return {**state, "label_failed_ids": failures}



def finalize_node(state: dict) -> dict:
    """
    Marks all successfully processed emails as done in Supabase.
    Deduplicates IDs first — Send() fan-out or Gmail API quirks can
    occasionally produce the same email ID more than once in one run.
    """
    failed_label_ids = set(state.get("label_failed_ids", []))
    successful_handled = [
        email for email in state.get("handled", [])
        if email.get("success") is True and email["id"] not in failed_label_ids
    ]
    email_ids = list({
        email["id"]
        for email in successful_handled
    })
    mark_as_processed(email_ids)
    for email in successful_handled:
        sender = email.get("sender")
        if not sender:
            continue
        record_sender_memory(
            sender, email.get("labels", []), email.get("importance_score", 0),
            email.get("action", "unknown"), True,
        )
    logger.info("Marked %d emails as processed", len(email_ids))
    return state