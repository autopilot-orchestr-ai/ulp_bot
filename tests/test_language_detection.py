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


def test_detect_lang_falls_back_to_default_for_empty_text():
    assert detect_lang("", default="en") == "en"
    assert detect_lang("   ", default="cs") == "cs"
