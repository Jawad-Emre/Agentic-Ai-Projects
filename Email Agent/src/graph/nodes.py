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

from langchain_core.messages import SystemMessage, AIMessage, ToolMessage , HumanMessage
from src.graph.tools import build_email_tools
from src.llm.prompts import DECISION_SYSTEM_PROMPT


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


def fetch_unread_node(state: dict) -> dict:
    """Fetches unread emails and filters out already-processed ones."""
    emails = fetch_unread_emails()
    new_emails = filter_unprocessed(emails)
    print(f"Fetched {len(emails)} unread, {len(new_emails)} are new.")
    return {"raw_emails": new_emails}


def run_agent_for_email(email: dict) -> dict:
    """
    Full per-email agentic loop, run as a single Send() target:
    seed context -> LLM decides action -> execute the chosen tool.
    Kept as one node because per-email state (messages) doesn't
    survive being split across separate graph nodes in this topology.
    """
    prompt = DECISION_SYSTEM_PROMPT.format(
        sender=email["sender"],
        subject=email["subject"],
        body=email["body"][:3000],
        labels=email.get("labels", []),
        importance_score=email.get("importance_score", 0),
        needs_reply=email.get("needs_reply", False),
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
            print(f"  Model '{model_name}' failed in decide_action: {str(e)[:200]}")
            continue

    if response is None or not getattr(response, "tool_calls", None):
        print(f"⚠️ No action decided for '{email.get('subject', 'UNKNOWN')}': {last_error}")
        return {"handled": [{**email, "action": "none"}]}

    tool_map = {t.name: t for t in tools}
    action_taken = "none"
    for call in response.tool_calls:
        tool_fn = tool_map.get(call["name"])
        if tool_fn:
            tool_fn.invoke(call["args"])
            action_taken = call["name"]

    return {"handled": [{**email, "action": action_taken}]}



def apply_labels_node(state: dict) -> dict:
    """Writes classification labels back to Gmail for all processed emails."""
    apply_labels_batch(state["processed"])
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