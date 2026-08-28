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


@pytest.mark.parametrize(
    "text",
    [
        # Regression: a real production message. Ukrainian and Russian share
        # nearly the entire Cyrillic alphabet, and this sentence contains
        # none of either language's diagnostic-only letters (і/ї/є/ґ for uk,
        # ы/э/ъ/ё for ru) - langdetect's statistical model genuinely guesses
        # "ru" for it, even though it's unambiguously Ukrainian to a human
        # and the conversation had already established "uk".
        "Як довго чекати?",
        "Так куди ви подзвоните якщо у вас нема мого номера?",
    ],
)
def test_detect_lang_prefers_established_language_when_uk_ru_ambiguous(text):
    assert detect_lang(text, default="uk") == "uk"


def test_detect_lang_prefers_established_russian_when_uk_ru_ambiguous():
    # Same ambiguous-text mechanism, opposite direction: this isn't a
    # uk-specific hardcode, it preserves whatever language was established.
    assert detect_lang("Как долго ждать?", default="ru") == "ru"


def test_detect_lang_still_switches_to_russian_with_diagnostic_letters():
    # A genuinely Russian-diagnostic sentence (ы) must still override an
    # established Ukrainian default - the fix narrows ambiguous-text
    # behavior, it doesn't disable uk<->ru switching entirely.
    assert detect_lang("Мы будем рады вам помочь", default="uk") == "ru"


def test_detect_lang_still_switches_to_ukrainian_with_diagnostic_letters():
    assert detect_lang("Дякую, все зрозуміло", default="ru") == "uk"


@pytest.mark.parametrize(
    "text",
    [
        # Regression, client-reported 2026-08-28: langdetect confidently
        # (99.99%) detects these as "ru" - unlike the ambiguous cases above,
        # this is langdetect getting it right - but the old diagnostic-letter
        # -only check discarded that and kept the established "uk" anyway,
        # since neither sentence contains і/ї/є/ґ/ы/э/ъ/ё. Every word here
        # (мне/нужна/нужно/перевод/также) is lexically exclusive to Russian -
        # the Ukrainian equivalents are мені/потрібна/потрібно/переклад/також
        # (different spelling) - so a word-level match is as safe as the
        # existing letter-level one.
        "Мне нужна консультация",
        "Перевод документов также",
    ],
)
def test_detect_lang_switches_to_russian_via_diagnostic_words(text):
    assert detect_lang(text, default="uk") == "ru"


def test_detect_lang_switches_to_ukrainian_via_diagnostic_words():
    # "Дякую"/"чому" contain no і/ї/є/ґ either - this specifically exercises
    # the new word-level signal, not the pre-existing letter one.
    assert detect_lang("Дякую, чому так довго?", default="ru") == "uk"


@pytest.mark.parametrize(
    "text",
    [
        # Regression, client-reported 2026-08-28: diacritic-free Czech
        # doesn't land anywhere near "cs" in langdetect's own ranked
        # candidates - verified against the real library: these six
        # sentences each got a different wrong top guess (sk/ro/hr/sl/pl/hu),
        # never "cs", so the "scan all ranked candidates" fix above can't
        # help here - there's no "cs" candidate to find.
        "Potrebovala bych konzultaci",
        "Konzultace",
        "Chci se zeptat na cenu",
        "Kolik to stoji?",
        "Potrebuji pravnika",
    ],
)
def test_detect_lang_falls_back_to_czech_lexical_signal(text):
    assert detect_lang(text, default="uk") == "cs"


def test_detect_lang_czech_lexical_signal_works_with_diacritics_too():
    assert detect_lang("Potřebovala bych konzultaci", default="uk") == "cs"
