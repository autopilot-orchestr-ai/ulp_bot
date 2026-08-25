from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.agent_rules.strings import WHEN_WILL_YOU_CALL_RESPONSE
from src.bots.utils.language_detection import detect_lang
from src.logger import log_event


async def call_timing_reply(state: AgentState) -> dict:
    """User is asking when staff will contact them, outside the lead-capture form
    (the in-form version of this question is handled directly inside lead_capture.py)."""
    log_event("call_timing_question", status="ok", question=state.incoming.text)

    client_lang = state.language or (detect_lang(state.incoming.text) if state.incoming.text else "uk")
    return {"response": WHEN_WILL_YOU_CALL_RESPONSE.get(client_lang, WHEN_WILL_YOU_CALL_RESPONSE["uk"])}