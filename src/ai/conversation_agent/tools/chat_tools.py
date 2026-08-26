"""LangChain tool definitions used by the `chat` node (nodes/chat.py)."""
from uuid import UUID

from langchain_core.tools import tool

from src.api_client.core_api import core_api
from src.logger import log_event


def build_log_unanswered_question_tool(conversation_id: UUID):
    """Returns a `log_unanswered_question` tool scoped to the current
    conversation, so the DB row stays linked to the real conversation
    (the old nodes/escalation.py stubbed a fresh uuid4() here instead and
    silently orphaned every logged question — not carried forward)."""

    @tool
    async def log_unanswered_question(question: str) -> str:
        """Call this when the user's question is about the firm or its
        services but isn't covered anywhere in the COMPANY INFORMATION you
        were given - for example, a request for legal advice on their
        specific situation, or a procedural detail genuinely not listed.
        Do not call this for questions unrelated to the firm."""
        try:
            await core_api.store_unanswered_question(
                conversation_id=conversation_id,
                question_text=question,
            )
            log_event("unanswered_question_logged", status="ok", question=question)
        except Exception as exc:
            log_event("unanswered_question_logged", status="error", error=str(exc))
        return "logged"

    return log_unanswered_question
