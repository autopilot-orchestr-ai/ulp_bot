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


def test_is_affirmative_matches_widened_word_set():
    for word in ("ok", "добре", "sure"):
        assert is_affirmative(word) is True


def test_is_negative_does_not_false_positive_on_words_starting_with_ne():
    # Regression: "nevím" ("I don't know") and "nemám čas" ("I don't have time")
    # both start with "ne" but are not declines - startswith matching used to
    # misclassify them and silently wipe the user's in-progress form.
    assert is_negative("nevím") is False
    assert is_negative("nemám čas") is False


def test_is_negative_whole_token_match_still_works_with_trailing_text():
    assert is_negative("ні, дякую") is True
    assert is_negative("no thanks") is True
