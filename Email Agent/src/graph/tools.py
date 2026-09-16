"""
Tool definitions for the agentic email-handling loop.
Tools are built per-email via a factory so each tool call acts on the
correct email's real Gmail id/thread_id without asking the LLM to
supply those (avoids hallucinated IDs).
"""

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from src.gmail.drafts import create_draft_reply
from src.gmail.labels import apply_labels_to_email, archive_email
from src.llm.client import get_llm, MODEL_FALLBACK_CHAIN
from src.llm.prompts import DRAFT_REPLY_PROMPT_TEMPLATE


class ReasonInput(BaseModel):
    reasoning: str = Field(description="One-line reason for choosing this action.")


def build_email_tools(email: dict) -> list:
    """
    Returns tools bound to THIS email via closure. The LLM only ever
    supplies 'reasoning' — real email data (id, thread_id, etc.) is
    captured here, never passed through the LLM.
    """

    def _draft_reply(reasoning: str) -> str:
        prompt = DRAFT_REPLY_PROMPT_TEMPLATE.format(
            sender=email["sender"],
            subject=email["subject"],
            body=email["body"][:3000],
        )
        draft_text = None
        for model_name in MODEL_FALLBACK_CHAIN:
            try:
                llm = get_llm(model_name=model_name, temperature=0.4)
                response = llm.invoke(prompt)
                content = response.content
                if isinstance(content, list):
                    draft_text = next(
                        (b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text"),
                        str(content),
                    )
                else:
                    draft_text = content
                break
            except Exception:
                continue

        if not draft_text:
            raise RuntimeError("Failed to generate draft after trying all models")

        drafted_email = {**email, "draft": draft_text.strip()}
        create_draft_reply(drafted_email)
        return f"Draft created and saved to Gmail. Reason: {reasoning}"

    def _flag_for_review(reasoning: str) -> str:
        apply_labels_to_email(email["id"], ["Needs-Reply"])
        return f"Flagged for manual review. Reason: {reasoning}"

    def _archive_no_action(reasoning: str) -> str:
        if email.get("importance_score", 0) >= 0.8:
            raise RuntimeError("High-importance email cannot be archived automatically")
        archive_email(email["id"])
        return f"Email archived. Reason: {reasoning}"

    return [
        StructuredTool.from_function(
            func=_draft_reply,
            name="draft_reply",
            description="Draft a reply and save to Gmail Drafts. Use when a genuine human response is expected.",
            args_schema=ReasonInput,
        ),
        StructuredTool.from_function(
            func=_flag_for_review,
            name="flag_for_review",
            description="Flag for manual review without drafting. Use when ambiguous or sensitive.",
            args_schema=ReasonInput,
        ),
        StructuredTool.from_function(
            func=_archive_no_action,
            name="archive_no_action",
            description="Take no action. Use for newsletters, alerts, or anything not needing a response.",
            args_schema=ReasonInput,
        ),
    ]