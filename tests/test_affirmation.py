from src.ai.conversation_agent.agent_rules.affirmation import is_affirmative, is_negative


def test_is_affirmative_matches_known_words():
    for word in ("yes", "так", "да", "ano", "chci", "y", "Yes", "ТАК"):
        assert is_affirmative(word) is True


def test_is_affirmative_rejects_unrelated_text():
    assert is_affirmative("no") is False
    assert is_affirmative("hello") is False
    assert is_affirmative("") is False


def test_is_negative_matches_known_words():
    for word in ("no", "ні", "нет", "ne", "No", "НІ"):
        assert is_negative(word) is True


def test_is_negative_rejects_unrelated_text():
    assert is_negative("yes") is False
    assert is_negative("hello") is False
    assert is_negative("") is False
