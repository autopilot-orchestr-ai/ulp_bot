from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.ai.conversation_agent.agent_rules.form_validator import FormValidator
from src.ai.conversation_agent.agent_rules.strings import WEEKEND_NOTICES
from src.ai.conversation_agent.prompts.chat import SYSTEM_PROMPT
from src.ai.conversation_agent.prompts.handoff import HANDOFF_MESSAGES
from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.tools.chat_tools import build_log_unanswered_question_tool
from src.ai.llm import get_llm
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

    # Fast-path, mirrors lead_capture.py's _check_call_timing: this used to
    # only have exact-wording guarantees inside an active lead form (the
    # standalone node that handled it everywhere else was removed in the
    # 2026-08-26 graph refactor - an unintentional gap, not a deliberate
    # decision). No LLM call needed for this one.
    # Per user policy (2026-08-27): this intercept fires before any contact
    # details are ever collected, so it must not promise a callback we have
    # no way to make - redirect to the firm's own contact channels instead
    # (the same HANDOFF_MESSAGES used below), not a "we'll call you" promise.
    if FormValidator.is_asking_call_timing(state.incoming.text):
        response = HANDOFF_MESSAGES.get(lang, HANDOFF_MESSAGES["en"])
        if FormValidator.has_weekend_mention(state.incoming.text):
            response = WEEKEND_NOTICES.get(lang, WEEKEND_NOTICES["en"]) + response
        return {"response": response}

    log_unanswered_question = build_log_unanswered_question_tool(
        conversation_id=state.conversation_id
    )

    llm = get_llm(settings.llm_model).bind_tools([log_unanswered_question])

    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT.format(lang=lang, company_info=_read_company_info())
        ),
        *_history_messages(state.conversation_history),
        # Repeated right before the current turn, not just once at the top -
        # client-reported 2026-08-28: earlier turns in a long-running
        # conversation had drifted to mostly one language (uk), and even
        # though this turn's detected language was correctly cs/ru (see
        # `response_sent` logs), the model kept answering in uk anyway,
        # imitating the dominant pattern in the history instead of the
        # system prompt's language instruction - a long history dilutes an
        # instruction that only appears once, early in the context. Placing
        # it again as the very last thing before generation fixes that
        # regardless of how many prior turns used a different language.
        SystemMessage(
            content=(
                f"Reminder: earlier turns above may be in a different language. "
                f"Reply to the client's message below exclusively in {lang}, "
                f"regardless of what language previous turns used."
            )
        ),
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
