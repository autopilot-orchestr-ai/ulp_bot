import pytest

from src.bots.utils.language_detection import detect_lang


@pytest.mark.parametrize(
    "text,expected",
    [
        # Regression: langdetect misclassifies these in production
        # (detect("hello") == "fi", detect("hi") == "sw", detect("ahoj") == "so",
        # detect("привет") == "mk") - verified against the real langdetect library
        # before adding the fast-path entries that fix them.
        ("hello", "en"),
        ("Hello!", "en"),
        ("hi", "en"),
        ("hey", "en"),
        ("good morning", "en"),
        ("good day", "en"),
        ("ahoj", "cs"),
        ("Ahoj!", "cs"),
        ("čau", "cs"),
        ("dobrý den", "cs"),
        ("привіт", "uk"),
        ("Привіт!", "uk"),
        ("вітаю", "uk"),
        ("привет", "ru"),
        ("Привет!", "ru"),
        # Existing short-word fast path, unchanged
        ("так", "uk"),
        ("yes", "en"),
        ("ano", "cs"),
        ("да", "ru"),
    ],
)
def test_detect_lang_common_greetings(text, expected):
    assert detect_lang(text) == expected


def test_detect_lang_still_uses_real_detection_for_longer_text():
    """The fast-path additions above must not swallow real detection for
    text that isn't a bare greeting."""
    assert detect_lang("Скільки коштує апостиль?") == "uk"


@pytest.mark.parametrize(
    "text,expected",
    [
        # Regression: langdetect's #1 guess is a language we don't support
        # at all, even though a supported one is a real (if lower-ranked)
        # candidate. Verified against the real library: detect_langs("I need
        # a lawyer") == [cy:0.71, en:0.29] - "cy" (Welsh) was being trusted
        # as the sole answer, silently discarding "en".
        ("I need a lawyer", "en"),
        ("How much does it cost?", "en"),
        ("What are your working hours?", "en"),
        ("Потрібен юрист", "uk"),
        ("Хочу замовити довіреність", "uk"),
        ("Potřebuju právníka", "cs"),
    ],
)
def test_detect_lang_prefers_a_supported_candidate_over_top_unsupported_guess(text, expected):
    assert detect_lang(text) == expected


def test_detect_lang_falls_back_to_default_when_no_candidate_is_supported():
    """A genuinely unsupported language (no uk/cs/ru/en candidate at all)
    must still fall through to the default, not pick something arbitrary."""
    assert detect_lang("Ich brauche einen Anwalt", default="uk") == "uk"


def test_detect_lang_falls_back_to_default_for_empty_text():
    assert detect_lang("", default="en") == "en"
    assert detect_lang("   ", default="cs") == "cs"
