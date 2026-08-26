"""Shared yes/no word matching for the two places that need it:
gate.py's affirmative-reply-to-manager-prompt short-circuit, and
lead_capture.py's awaiting_contact_confirmation step. Not the same thing
as lead_capture.py's _SKIP_EMAIL_WORDS, which covers a more specific set
of "no email" phrasings for a different, unrelated prompt - that stays as
its own thing."""

AFFIRMATIVE_WORDS = {"ano", "yes", "так", "да", "chci", "y"}
NEGATIVE_WORDS = {"ні", "нет", "no", "ne"}


def is_affirmative(text: str) -> bool:
    text_lower = text.lower().strip()
    return text_lower == "a" or any(text_lower.startswith(w) for w in AFFIRMATIVE_WORDS)


def is_negative(text: str) -> bool:
    text_lower = text.lower().strip()
    return any(text_lower.startswith(w) for w in NEGATIVE_WORDS)
