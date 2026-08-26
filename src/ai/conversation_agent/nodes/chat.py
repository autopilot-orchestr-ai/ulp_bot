from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.ai.conversation_agent.prompts.chat import SYSTEM_PROMPT
from src.ai.conversation_agent.prompts.handoff import HANDOFF_MESSAGES
from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.tools.chat_tools import build_log_unanswered_question_tool
from src.ai.knowledge.llm import get_llm
from src.config import settings
from src.logger import log_event


def _read_company_info() -> str:
    """Read fresh on every call - the whole point of this design is that
    editing the file takes effect on the very next message, with no reload
    or restart step. The file is small (well under a second to read)."""
    return Path(settings.company_info_path).read_text(encoding="utf-8")


def _history_messages(history: list[dict]) -> list:
    messages = []
    for entry in history:
        cls = HumanMessage if entry["role"] == "user" else AIMessage
        messages.append(cls(content=entry["content"]))
    return messages


async def chat_node(state: AgentState) -> dict:
    """One conversational node replacing the old info/off_topic/escalation
    split: FAQ answering, identity, off-topic redirects, and human handoff
    for unanswerable-but-relevant questions all live here now, grounded
    entirely in src/assets/company_info.md rather than retrieval."""
    lang = state.language or "uk"
    log_unanswered_question = build_log_unanswered_question_tool(
        conversation_id=state.conversation_id
    )

    llm = get_llm(settings.llm_model).bind_tools([log_unanswered_question])

    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT.format(lang=lang, company_info=_read_company_info())
        ),
        *_history_messages(state.conversation_history),
        HumanMessage(content=state.incoming.text),
    ]

    log_event("chat_calling", status="start", text=state.incoming.text)
    ai_message = await llm.ainvoke(messages)

    tool_calls = ai_message.tool_calls or []
    if not tool_calls:
        log_event("chat_replied", status="ok", tool_called=None)
        return {"response": ai_message.content}

    call = tool_calls[0]
    await log_unanswered_question.ainvoke(call["args"])
    log_event("chat_replied", status="ok", tool_called=call["name"])
    return {"response": HANDOFF_MESSAGES.get(lang, HANDOFF_MESSAGES["uk"])}
