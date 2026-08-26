from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.conversation_agent.nodes.gate import (
    classify_lead_intent,
    is_affirmative_reply_to_manager_prompt,
    LeadGateClassification,
)
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState
from src.schemas.ai.messages import IncomingMessage


def _incoming(text):
    return IncomingMessage(
        client_id="1", channel="telegram", text=text,
        timestamp=datetime.now(), client_name="Test",
    )


def _state(text, history=None, lead_step=None, language="uk"):
    return AgentState(
        incoming=_incoming(text),
        conversation_history=history or [],
        lead_step=lead_step,
        language=language,
    )


def test_affirmative_reply_detected_after_manager_prompt():
    history = [{"role": "assistant", "content": "Бажаєте, щоб з вами зв'язався менеджер? (Так / Ні)"}]
    assert is_affirmative_reply_to_manager_prompt("так", history) is True


def test_affirmative_reply_ignored_without_manager_prompt():
    history = [{"role": "assistant", "content": "Ось наші послуги."}]
    assert is_affirmative_reply_to_manager_prompt("так", history) is False


def test_affirmative_reply_ignored_for_unrelated_word():
    history = [{"role": "assistant", "content": "Бажаєте, щоб з вами зв'язався менеджер? (Так / Ні)"}]
    assert is_affirmative_reply_to_manager_prompt("ні дякую", history) is False


async def test_classify_lead_intent_short_circuits_on_affirmative_reply():
    history = [{"role": "assistant", "content": "contact you? (yes / no)"}]
    state = _state("yes", history=history)
    with patch("src.ai.conversation_agent.nodes.gate.get_llm") as get_llm:
        result = await classify_lead_intent(state)
    get_llm.assert_not_called()
    assert result["route"] == Route.LEAD
    assert result["intent"] == "lead"


async def test_classify_lead_intent_skips_llm_when_form_active():
    state = _state("some name text", lead_step="awaiting_name")
    with patch("src.ai.conversation_agent.nodes.gate.get_llm") as get_llm:
        result = await classify_lead_intent(state)
    get_llm.assert_not_called()
    assert result["route"] == Route.LEAD


async def test_classify_lead_intent_flags_profanity_mid_form_via_regex_no_llm():
    # "сука" matches PROFANITY_PATTERNS directly (confirmed against
    # src/ai/conversation_agent/agent_rules/strings.py:86-91); "ти тупий
    # бот" (masc. "тупий") does NOT match the \bтуп[аоыіеє]+[ая]?\b pattern,
    # which only covers "и" via the Ukrainian/Russian vowel class it lists.
    state = _state("ти сука, чому мовчиш?", lead_step="awaiting_name")
    with patch("src.ai.conversation_agent.nodes.gate.get_llm") as get_llm, \
         patch(
             "src.ai.conversation_agent.nodes.gate.notify_manager_aggressive_telegram",
             new_callable=AsyncMock,
         ) as notify:
        result = await classify_lead_intent(state)
    get_llm.assert_not_called()
    notify.assert_awaited_once()
    assert result["route"] == Route.LEAD


async def test_classify_lead_intent_mid_form_no_profanity_no_notify():
    state = _state("Іван Петренко", lead_step="awaiting_name")
    with patch("src.ai.conversation_agent.nodes.gate.get_llm") as get_llm, \
         patch(
             "src.ai.conversation_agent.nodes.gate.notify_manager_aggressive_telegram",
             new_callable=AsyncMock,
         ) as notify:
        result = await classify_lead_intent(state)
    get_llm.assert_not_called()
    notify.assert_not_awaited()
    assert result["route"] == Route.LEAD


async def test_classify_lead_intent_routes_to_chat_when_llm_says_no():
    state = _state("Скільки коштує апостиль?")
    fake_structured = MagicMock()
    fake_structured.ainvoke = AsyncMock(
        return_value=LeadGateClassification(wants_lead=False, is_aggressive=False)
    )
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured
    with patch("src.ai.conversation_agent.nodes.gate.get_llm", return_value=fake_llm):
        result = await classify_lead_intent(state)
    assert result["route"] == Route.CHAT
    assert result["intent"] == "chat"


async def test_classify_lead_intent_routes_to_lead_when_llm_says_yes():
    state = _state("Хочу замовити довіреність, зателефонуйте мені")
    fake_structured = MagicMock()
    fake_structured.ainvoke = AsyncMock(
        return_value=LeadGateClassification(wants_lead=True, is_aggressive=False)
    )
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured
    with patch("src.ai.conversation_agent.nodes.gate.get_llm", return_value=fake_llm):
        result = await classify_lead_intent(state)
    assert result["route"] == Route.LEAD
    assert result["intent"] == "lead"


async def test_classify_lead_intent_notifies_on_aggressive_message():
    state = _state("ти тупий бот")
    fake_structured = MagicMock()
    fake_structured.ainvoke = AsyncMock(
        return_value=LeadGateClassification(wants_lead=False, is_aggressive=True)
    )
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured
    with patch("src.ai.conversation_agent.nodes.gate.get_llm", return_value=fake_llm), \
         patch(
             "src.ai.conversation_agent.nodes.gate.notify_manager_aggressive_telegram",
             new_callable=AsyncMock,
         ) as notify:
        await classify_lead_intent(state)
    notify.assert_awaited_once()


async def test_classify_lead_intent_survives_notify_failure():
    state = _state("ти тупий бот")
    fake_structured = MagicMock()
    fake_structured.ainvoke = AsyncMock(
        return_value=LeadGateClassification(wants_lead=False, is_aggressive=True)
    )
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured
    with patch("src.ai.conversation_agent.nodes.gate.get_llm", return_value=fake_llm), \
         patch(
             "src.ai.conversation_agent.nodes.gate.notify_manager_aggressive_telegram",
             new_callable=AsyncMock,
             side_effect=RuntimeError("telegram down"),
         ):
        result = await classify_lead_intent(state)  # must not raise
    assert result["route"] == Route.CHAT
