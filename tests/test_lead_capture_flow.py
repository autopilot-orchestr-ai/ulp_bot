from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.ai.conversation_agent.nodes.lead_capture import (
    _step_start,
    _step_awaiting_service,
    _step_awaiting_consultation_type,
    _step_awaiting_contact_confirmation,
)
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState
from src.schemas.ai.messages import IncomingMessage


def _incoming(text):
    return IncomingMessage(
        client_id="1", channel="telegram", text=text,
        timestamp=datetime.now(), client_name="Test",
    )


def _state(text, history=None, language="uk", **kwargs):
    return AgentState(
        incoming=_incoming(text),
        conversation_history=history or [],
        language=language,
        **kwargs,
    )


# --- _step_start: ambiguous consultation ---

async def test_step_start_ambiguous_consultation_asks_which_type():
    state = _state("потрібна консультація")
    result = await _step_start(state)
    assert result["lead_step"] == "awaiting_consultation_type"
    assert "юридична" in result["response"].lower() or "візова" in result["response"].lower()


# --- _step_start: concrete service, price not yet shown ---

async def test_step_start_concrete_service_no_price_hands_to_chat():
    state = _state("потрібен юрист")
    result = await _step_start(state)
    assert result.get("route_to_llm") is True
    assert result["current_service"] == "legal_consultation"


# --- _step_start: concrete service, price already shown ---

async def test_step_start_concrete_service_price_shown_asks_confirmation():
    history = [{"role": "assistant", "content": "Consultation costs 1900 CZK"}]
    state = _state("потрібен юрист", history=history)
    result = await _step_start(state)
    assert result["lead_step"] == "awaiting_contact_confirmation"
    assert result["current_service"] == "legal_consultation"


# --- _step_awaiting_service: price shown now goes to confirmation, not name ---

async def test_step_awaiting_service_price_shown_lands_on_confirmation_not_name():
    history = [{"role": "assistant", "content": "Apostille costs 4000 CZK"}]
    state = _state("апостиль", history=history)
    result = await _step_awaiting_service(state)
    assert result["lead_step"] == "awaiting_contact_confirmation"
    assert result["current_service"] == "apostille"


# --- _step_awaiting_consultation_type ---

async def test_step_awaiting_consultation_type_resolves_legal():
    state = _state("юридична", lead_step="awaiting_consultation_type")
    result = await _step_awaiting_consultation_type(state)
    assert result["current_service"] == "legal_consultation"


async def test_step_awaiting_consultation_type_resolves_visa():
    state = _state("візова", lead_step="awaiting_consultation_type")
    result = await _step_awaiting_consultation_type(state)
    assert result["current_service"] == "visa_consultation"


async def test_step_awaiting_consultation_type_reprompts_when_still_unclear():
    state = _state("не знаю", lead_step="awaiting_consultation_type")
    with patch(
        "src.ai.conversation_agent.nodes.lead_capture.FormValidator.is_user_asking_question",
        new_callable=AsyncMock, return_value=False,
    ):
        result = await _step_awaiting_consultation_type(state)
    assert result.get("lead_step") is None  # unchanged (reprompt) - caller keeps current step
    assert "юридична" in result["response"].lower() or "візова" in result["response"].lower()


async def test_step_awaiting_consultation_type_hands_off_on_question():
    state = _state("скільки це коштує?", lead_step="awaiting_consultation_type")
    with patch(
        "src.ai.conversation_agent.nodes.lead_capture.FormValidator.is_user_asking_question",
        new_callable=AsyncMock, return_value=True,
    ):
        result = await _step_awaiting_consultation_type(state)
    assert result.get("route_to_llm") is True


# --- _step_awaiting_contact_confirmation ---

async def test_step_awaiting_contact_confirmation_yes_advances_to_name():
    state = _state("так", lead_step="awaiting_contact_confirmation", current_service="apostille")
    result = await _step_awaiting_contact_confirmation(state)
    assert result["lead_step"] == "awaiting_name"
    assert result["route"] == Route.LEAD


async def test_step_awaiting_contact_confirmation_no_resets_and_declines():
    state = _state(
        "ні", lead_step="awaiting_contact_confirmation", current_service="apostille",
        client_name="should be cleared",
    )
    result = await _step_awaiting_contact_confirmation(state)
    assert result["lead_step"] is None
    assert result["current_service"] is None
    assert result["client_name"] is None


async def test_step_awaiting_contact_confirmation_question_hands_off():
    state = _state("а скільки коштує?", lead_step="awaiting_contact_confirmation", current_service="apostille")
    with patch(
        "src.ai.conversation_agent.nodes.lead_capture.FormValidator.is_user_asking_question",
        new_callable=AsyncMock, return_value=True,
    ):
        result = await _step_awaiting_contact_confirmation(state)
    assert result.get("route_to_llm") is True


async def test_step_awaiting_contact_confirmation_unclear_reprompts():
    state = _state("хм", lead_step="awaiting_contact_confirmation", current_service="apostille")
    with patch(
        "src.ai.conversation_agent.nodes.lead_capture.FormValidator.is_user_asking_question",
        new_callable=AsyncMock, return_value=False,
    ):
        result = await _step_awaiting_contact_confirmation(state)
    assert result.get("lead_step") is None  # unchanged, caller keeps current step
    assert result.get("route_to_llm") is not True
