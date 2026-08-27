"""Shared yes/no word matching for the two places that need it:
gate.py's affirmative-reply-to-manager-prompt short-circuit, and
lead_capture.py's awaiting_contact_confirmation step. Not the same thing
as lead_capture.py's _SKIP_EMAIL_WORDS, which covers a more specific set
of "no email" phrasings for a different, unrelated prompt - that stays as
its own thing."""

import re

AFFIRMATIVE_WORDS = {
    "ano", "yes", "так", "да", "chci", "y", "ok", "okay", "добре", "хочу",
    "давай", "sure", "jasně", "звичайно", "конечно", "souhlasím",
}
NEGATIVE_WORDS = {"ні", "нет", "no", "ne"}


def is_affirmative(text: str) -> bool:
    text_lower = text.lower().strip()
    return text_lower == "a" or any(text_lower.startswith(w) for w in AFFIRMATIVE_WORDS)


def is_negative(text: str) -> bool:
    text_lower = text.lower().strip()
    tokens = re.findall(r"\w+", text_lower)
    return bool(tokens) and tokens[0] in NEGATIVE_WORDS
