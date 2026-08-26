from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.ai.conversation_agent.nodes.lead_capture import _step_awaiting_email
from src.ai.conversation_agent.state import AgentState
from src.schemas.ai.messages import IncomingMessage


def _state(text, language="en", **kwargs):
    incoming = IncomingMessage(
        client_id="1", channel="telegram", text=text,
        timestamp=datetime.now(), client_name="Test",
    )
    return AgentState(incoming=incoming, language=language, lead_step="awaiting_email", **kwargs)


def _mock_hostility_llm():
    """FormValidator.extract_email always calls is_profanity_or_hostile first,
    which calls the LLM - mock it to return a clean "FALSE" verdict."""
    fake_response = AsyncMock()
    fake_response.content = "FALSE"
    fake_llm = AsyncMock()
    fake_llm.ainvoke = AsyncMock(return_value=fake_response)
    return patch(
        "src.ai.conversation_agent.agent_rules.form_validator.get_llm",
        return_value=fake_llm,
    )


async def test_step_awaiting_email_reprompts_without_crashing_on_invalid_email():
    """Regression test for a real production incident: this crashed with
    AttributeError: 'AgentState' object has no attribute 'msg', taking down
    the whole graph invocation uncaught. Because the crash happened before
    notify_manager_lead_telegram (only called in the success branch below),
    a fully-captured lead (name + phone already collected in prior turns)
    was silently dropped - the manager was never notified. Triggered by a
    gibberish test email ("fajksdfdfg@gh.com") that FormValidator.extract_email
    correctly rejects via its consonant-run heuristic."""
    state = _state("fajksdfdfg@gh.com", client_name="Alex Test", client_phone="5678372654")
    with _mock_hostility_llm():
        result = await _step_awaiting_email(state)  # must not raise
    assert result["response"]
    assert "@" not in result.get("client_email", "")  # no email captured


async def test_step_awaiting_email_reprompt_is_language_aware():
    state = _state("fajksdfdfg@gh.com", language="uk")
    with _mock_hostility_llm():
        result = await _step_awaiting_email(state)
    assert "адрес" in result["response"].lower()  # Ukrainian EMAIL_REPROMPT wording, not the English one


async def test_step_awaiting_email_accepts_valid_email_and_notifies_manager():
    state = _state("real.person@example.com", client_name="Alex Test", client_phone="+420700000000")
    with _mock_hostility_llm(), patch(
        "src.ai.conversation_agent.nodes.lead_capture.notify_manager_lead_telegram",
        new_callable=AsyncMock,
    ) as notify:
        result = await _step_awaiting_email(state)
    notify.assert_awaited_once()
    assert result["lead_step"] == "completed"
    assert result["client_email"] == "real.person@example.com"


async def test_step_awaiting_email_skip_word_completes_without_email():
    state = _state("no", client_name="Alex Test", client_phone="+420700000000")
    with _mock_hostility_llm(), patch(
        "src.ai.conversation_agent.nodes.lead_capture.notify_manager_lead_telegram",
        new_callable=AsyncMock,
    ) as notify:
        result = await _step_awaiting_email(state)
    notify.assert_awaited_once()
    assert result["lead_step"] == "completed"
    assert result["client_email"] is None
