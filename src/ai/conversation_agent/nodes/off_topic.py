from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.prompts.escalation import OFF_TOPIC_MESSAGES
from src.ai.conversation_agent.agent_rules.lang import detect_lang
from src.logger import log_event


async def off_topic_reply(state: AgentState) -> dict:
    """A question with nothing to do with the firm (weather, chit-chat, etc.) —
    a short redirect, not the escalation handoff, since no human at the firm
    could actually help with it. No DB logging or staff notification."""
    log_event("off_topic", status="ok", question=state.incoming.text)

    client_lang = state.language or (detect_lang(state.incoming.text) if state.incoming.text else "uk")

    return {"response": OFF_TOPIC_MESSAGES.get(client_lang, OFF_TOPIC_MESSAGES["uk"])}