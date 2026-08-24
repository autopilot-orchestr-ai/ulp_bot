from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.agent_rules.strings import WHEN_WILL_YOU_CALL_RESPONSE
from src.logger import log_event


async def call_timing_reply(state: AgentState) -> dict:
    """User is asking when staff will contact them, outside the lead-capture form
    (the in-form version of this question is handled directly inside lead_capture.py)."""
    log_event("call_timing_question", status="ok", question=state.incoming.text)

    lang = state.language or "uk"
    return {"response": WHEN_WILL_YOU_CALL_RESPONSE.get(lang, WHEN_WILL_YOU_CALL_RESPONSE["uk"])}