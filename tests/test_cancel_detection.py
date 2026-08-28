from unittest.mock import AsyncMock, patch

from src.ai.conversation_agent.agent_rules.form_validator import FormValidator


async def test_is_user_cancelling_true_for_explicit_keyword():
    assert await FormValidator.is_user_cancelling("скасуйте, будь ласка") is True


async def test_is_user_cancelling_false_for_plain_answer():
    assert await FormValidator.is_user_cancelling("Іван Петренко") is False


async def test_is_user_cancelling_does_not_call_llm_at_all():
    """Regression guard for the 2026-08-28 client report: is_user_cancelling
    used to also short-circuit True on is_profanity_or_hostile (an LLM
    call), which wiped an in-progress lead form ("Катерина Мат" - a
    truncated surname containing "мат", the RU/UK noun for "swearing" -
    got flagged as hostile and cancelled the whole booking). Cancellation
    must now be judged purely by CANCEL_KEYWORDS, with no model call
    involved, so a false-positive hostility read can no longer destroy an
    active form."""
    with patch(
        "src.ai.conversation_agent.agent_rules.form_validator.get_llm"
    ) as get_llm:
        result = await FormValidator.is_user_cancelling("Катерина Мат")
    get_llm.assert_not_called()
    assert result is False
