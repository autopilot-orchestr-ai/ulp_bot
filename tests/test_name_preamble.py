from unittest.mock import AsyncMock, patch

from src.ai.conversation_agent.agent_rules.form_validator import FormValidator


def _mock_llm_sequence(*verdicts: str):
    """is_valid_name calls the LLM twice - once for the profanity check
    (first), once for the name-validity check (second). Mock each call's
    response in order via side_effect."""
    responses = []
    for v in verdicts:
        r = AsyncMock()
        r.content = v
        responses.append(r)
    fake_llm = AsyncMock()
    fake_llm.ainvoke = AsyncMock(side_effect=responses)
    return patch(
        "src.ai.conversation_agent.agent_rules.form_validator.get_llm",
        return_value=fake_llm,
    )


def test_strips_czech_preamble():
    # Regression: a production test on 2026-08-27 sent this exact sentence
    # and got hard-rejected by is_valid_name's word-count gate (5 words > 4)
    # before validation ever ran - phone/email capture already tolerate full
    # sentences via regex-search, name capture didn't.
    assert FormValidator.strip_name_preamble("Moje jméno je Alex Test") == "Alex Test"


def test_strips_english_preamble():
    assert FormValidator.strip_name_preamble("my name is Alex Test") == "Alex Test"
    assert FormValidator.strip_name_preamble("I am Alex Test") == "Alex Test"


def test_strips_ukrainian_preamble():
    assert FormValidator.strip_name_preamble("мене звати Олександр") == "Олександр"


def test_strips_russian_preamble():
    assert FormValidator.strip_name_preamble("меня зовут Александр") == "Александр"


def test_leaves_bare_name_untouched():
    assert FormValidator.strip_name_preamble("Alex Test") == "Alex Test"


def test_is_idempotent_on_already_stripped_text():
    once = FormValidator.strip_name_preamble("Moje jméno je Alex Test")
    twice = FormValidator.strip_name_preamble(once)
    assert once == twice == "Alex Test"


def test_handles_empty_text():
    assert FormValidator.strip_name_preamble("") == ""


async def test_is_valid_name_no_longer_hard_rejects_full_sentence_before_llm():
    # Before the preamble-strip fix, this failed the word-count gate (5 words)
    # and never reached the LLM at all - is_valid_name returned False
    # unconditionally. Now it should reach the (mocked) LLM call and honor
    # its TRUE verdict.
    with _mock_llm_sequence("FALSE", "TRUE"):  # not profane, then: valid name
        result = await FormValidator.is_valid_name("Moje jméno je Alex Test")
    assert result is True
