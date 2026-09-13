"""
Graph nodes for the email agent.
"""

from pydantic import ValidationError
from src.llm.client import get_llm , MODEL_FALLBACK_CHAIN
from src.llm.prompts import EmailClassification, CLASSIFICATION_PROMPT_TEMPLATE
from src.graph.state import EmailState

from src.llm.prompts import DRAFT_REPLY_PROMPT_TEMPLATE

from src.gmail.labels import apply_labels_batch
from src.gmail.drafts import create_draft_reply
from src.storage.processed_store import mark_as_processed
from src.gmail.fetch import fetch_unread_emails
from src.storage.processed_store import filter_unprocessed

# Caps concurrent Gemini calls to stay under free-tier per-minute token limits.
# Even though LangGraph's Send() fans out in parallel, this semaphore forces
# only N classifications to actually run at once.

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
            print(f"  Model '{model_name}' failed, trying next... ({str(e)[:80]})")
            continue

    if result is None:
        print(f"⚠️ All models failed for '{email['subject']}': {last_error}")
        result = EmailClassification(
            labels=["Other"], importance_score=0.3, needs_reply=False,
            reasoning=f"All models exhausted. Last error: {str(last_error)[:100]}"
        )

    classified: EmailState = {
        **email, "labels": result.labels, "importance_score": result.importance_score,
        "needs_reply": result.needs_reply, "reasoning": result.reasoning,
    }
    return {"processed": [classified]}



def draft_reply(email: dict) -> dict:
    """
    Generates a reply draft for an email flagged needs_reply=True.
    Returns the email dict with an added 'draft' field.
    """
    llm = get_llm(temperature=0.4)  # slightly higher: more natural phrasing

    prompt = DRAFT_REPLY_PROMPT_TEMPLATE.format(
        sender=email["sender"],
        subject=email["subject"],
        body=email["body"][:3000]
    )

    response = llm.invoke(prompt)

    # Handle thinking-block content format (same pattern as before)
    if isinstance(response.content, list):
        draft_text = next(
            (block["text"] for block in response.content if isinstance(block, dict) and block.get("type") == "text"),
            str(response.content)
        )
    else:
        draft_text = response.content

    return {**email, "draft": draft_text.strip()}



def fetch_unread_node(state: dict) -> dict:
    """Fetches unread emails and filters out already-processed ones."""
    emails = fetch_unread_emails()
    new_emails = filter_unprocessed(emails)
    print(f"Fetched {len(emails)} unread, {len(new_emails)} are new.")
    return {"raw_emails": new_emails}


def apply_labels_node(state: dict) -> dict:
    """Writes classification labels back to Gmail for all processed emails."""
    apply_labels_batch(state["processed"])
    return state


def draft_reply_node(email: dict) -> dict:
    """
    Send()-target wrapper: generates a draft for one email and
    immediately saves it to Gmail as a real draft.
    """
    drafted = draft_reply(email)
    create_draft_reply(drafted)
    print(f"Draft created for: {drafted['subject'][:50]}")
    return {"drafted": [drafted]}


def skip_drafting_node(state: dict) -> dict:
    """No-op node — used when no emails in this run need a reply."""
    print("No emails need a reply this cycle.")
    return state


def finalize_node(state: dict) -> dict:
    """
    Marks all successfully processed emails as done in Supabase.
    Deduplicates IDs first — Send() fan-out or Gmail API quirks can
    occasionally produce the same email ID more than once in one run.
    """
    email_ids = list({e["id"] for e in state["processed"]})  # set removes dupes
    mark_as_processed(email_ids)
    print(f"Marked {len(email_ids)} emails as processed.")
    return state