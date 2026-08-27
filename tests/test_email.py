import re
from unittest.mock import AsyncMock, patch

from src.ai.conversation_agent.agent_rules.form_validator import FormValidator


def _mock_hostility_llm():
    """extract_email always calls is_profanity_or_hostile first, which calls
    the LLM - mock it to return a clean "FALSE" verdict."""
    fake_response = AsyncMock()
    fake_response.content = "FALSE"
    fake_llm = AsyncMock()
    fake_llm.ainvoke = AsyncMock(return_value=fake_response)
    return patch(
        "src.ai.conversation_agent.agent_rules.form_validator.get_llm",
        return_value=fake_llm,
    )


def test_consonant_heavy_prefix_is_syntactically_valid():
    # Sanity check that the address used below is a real, well-formed email -
    # a production test on 2026-08-27 hit this exact address and it was
    # wrongly rejected by extract_email's old consonant-run heuristic
    # (6+ consecutive consonants in the prefix), even though pm.me is a real
    # ProtonMail domain and the address is entirely valid.
    match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,10}\b', "Vrnlsn@pm.me")
    assert match is not None


async def test_extract_email_no_longer_rejects_consonant_heavy_prefix():
    with _mock_hostility_llm():
        result = await FormValidator.extract_email("my email is Vrnlsn@pm.me")
    assert result == "vrnlsn@pm.me"


async def test_extract_email_still_rejects_too_short_tld():
    with _mock_hostility_llm():
        result = await FormValidator.extract_email("test@x.c")
    assert result is None


async def test_extract_email_accepts_normal_email():
    with _mock_hostility_llm():
        result = await FormValidator.extract_email("real.person@example.com")
    assert result == "real.person@example.com"
