# Lead Capture Flow Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the lead-capture funnel so every service follows: clarify what's needed → show pricing → explicitly ask permission to collect contact details → only then collect name/phone/email — fixing real client-reported behavior where the bot jumped straight to asking for a name without ever clarifying (legal vs. visa consultation) or showing pricing. Also reinstate the exact-wording "when will you call me?" response (with its weekend special-case) everywhere the question can come up, not just mid-form.

**Architecture:** Two new deterministic `lead_capture` steps (`awaiting_consultation_type`, `awaiting_contact_confirmation`) inserted into the existing state machine; `SERVICE_PATTERNS` splits its conflated `"consultation"` entry into `legal_consultation`/`visa_consultation`/`consultation_ambiguous`; a shared affirmative/negative word-matching helper extracted for reuse between `gate.py` and `lead_capture.py`; a call-timing fast-path added to `chat_node` mirroring the one already in `lead_capture.py`.

**Tech Stack:** unchanged from the existing codebase — no new dependencies.

Full design spec: `docs/superpowers/specs/2026-08-27-lead-capture-flow-redesign-design.md` — read it once for the "why"; this plan is the "what exactly to type."

## Global Constraints

- `_step_awaiting_email`, `_step_awaiting_name`, `_step_awaiting_phone`, and everything downstream of `awaiting_name` are **out of scope** — untouched by this plan. Only the pre-name-collection portion of the funnel changes.
- `lead_capture_node`'s wrapper (`nodes/lead_capture.py:269-278`, unchanged by this plan) auto-computes `result["route"]` for anything returned by a **step handler** (not an intercept): `route_to_llm` truthy → `Route.CHAT`; `lead_step == "completed"` → `Route.END`; otherwise → `Route.LEAD` (which `graph.py`'s edge table maps to `END` for this turn regardless — the *next* real message resumes via `gate`'s mid-form check). A step handler's own `"route"` key is only meaningful for direct unit tests that call the handler function directly, bypassing this wrapper — it has no effect when the handler runs through the real `lead_capture_node`. Every new/changed handler in this plan follows the exact pattern already established by `_step_awaiting_name`/`_step_awaiting_phone` (explicitly set `"route": Route.LEAD` on a successful advance, for direct-test consistency) or by reprompt-style handlers like the `NAME_REPROMPT` branch (don't set `"route"` at all on a reprompt).
- `_SKIP_EMAIL_WORDS` (`nodes/lead_capture.py:40`) stays exactly as-is — it's for a different, more specific purpose (opting out of giving an email specifically) than the new yes/no contact-confirmation gate. Do not merge or reuse it for the new gate.
- Every new/changed string dict covers all 4 languages (en/uk/cs/ru), matching the tone and `**bold**` conventions already used by `PHONE_REPROMPT`/`NAME_REPROMPT`/`EMAIL_REPROMPT`/`SERVICES_LIST_RESPONSE`.
- Run `poetry run pytest -v` clean before every commit.

---

### Task 1: `SERVICE_PATTERNS` split + new copy

**Files:**
- Modify: `src/ai/conversation_agent/agent_rules/strings.py`
- Test: `tests/test_service_patterns.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `SERVICE_PATTERNS` now yields `"legal_consultation"` / `"visa_consultation"` / `"consultation_ambiguous"` instead of the old single `"consultation"`. `SERVICE_LOCALIZED_NAMES` has matching entries for the two new concrete IDs (the old `"consultation"` key is removed — nothing produces that ID anymore). New dicts `CONSULTATION_TYPE_PROMPT`, `CONTACT_CONFIRMATION_PROMPT`, `CONTACT_DECLINED_MESSAGE` — consumed by Task 3's `lead_capture.py` changes.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_service_patterns.py
from src.ai.conversation_agent.agent_rules.form_validator import FormValidator


def test_detect_service_distinguishes_legal_from_visa_consultation():
    assert FormValidator.detect_service("потрібен юрист") == "legal_consultation"
    assert FormValidator.detect_service("I need a lawyer") == "legal_consultation"
    assert FormValidator.detect_service("právník") == "legal_consultation"
    assert FormValidator.detect_service("потрібна віза") == "visa_consultation"
    assert FormValidator.detect_service("migration consultation") == "visa_consultation"
    assert FormValidator.detect_service("міграційна консультація") == "visa_consultation"


def test_detect_service_bare_consultation_is_ambiguous():
    assert FormValidator.detect_service("потрібна консультація") == "consultation_ambiguous"
    assert FormValidator.detect_service("konzultace") == "consultation_ambiguous"
    assert FormValidator.detect_service("I need a consultation") == "consultation_ambiguous"


def test_detect_service_other_services_unaffected():
    assert FormValidator.detect_service("переклад документів") == "translation"
    assert FormValidator.detect_service("апостиль") == "apostille"
    assert FormValidator.detect_service("довіреність") == "poa"
    assert FormValidator.detect_service("щось незрозуміле xyz") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_service_patterns.py -v`
Expected: FAIL — `assert 'consultation' == 'legal_consultation'` (or similar) for every consultation-related assertion; `SERVICE_PATTERNS` hasn't changed yet.

- [ ] **Step 3: Replace `SERVICE_PATTERNS` in `agent_rules/strings.py`**

Find this block (lines 35-47):

```python
SERVICE_PATTERNS = {
    # ⚖️ Consultations (Now includes právník, advokát, lawyer, etc.)
    r'кон[сзм][уь]?ль?т|юрист|віз|виз|poradenstv|konzultac|víz|viz|consult|legal|visa|právník|pravnik|advokát|advokat|lawyer|адвокат': "consultation",
    
    # ... keep the rest of your patterns exactly as we set them up earlier ...
    r'переклад|перевод|překlad|preklad|translat': "translation",
    r'довір|довер|pln[aeáé]\s?moc|plnou\s?moc|power\s?of\s?attorney': "poa",
    r'апостил|apostil': "apostille",
    r'заяв|згод|согласи|prohlášen|prohlasen|souhlas|statement|consent': "statement",
    r'несудим|trest|rejstřík|rejstrik|police\s?clearance|criminal': "police_clearance",
    r'одруж|брак|шлюб|свадьб|sňatk|snatk|svatb|marriag|weddin': "marriage",
    r'дублікат|дубликат|duplikát|duplikat|duplicat': "duplicates",
}
```

Replace with:

```python
SERVICE_PATTERNS = {
    # ⚖️ Legal consultations - distinct from visa/migration below (used to
    # be one conflated "consultation" bucket; a client reported the bot
    # never asking which type was meant).
    r'юрист|právník|pravnik|advokát|advokat|lawyer|адвокат|legal\s?consult|právní\s?konzult': "legal_consultation",
    # 🛂 Visa / migration consultations.
    r'віз|виз|víz|viz|visa|мігра|миграц|migra|migrant': "visa_consultation",
    # A bare "consultation" with neither legal nor visa qualifier - genuinely
    # ambiguous, handled by nodes/lead_capture.py's awaiting_consultation_type
    # step (asks which type before showing pricing).
    r'кон[сзм][уь]?ль?т|konzultac|consult|poradenstv': "consultation_ambiguous",

    r'переклад|перевод|překlad|preklad|translat': "translation",
    r'довір|довер|pln[aeáé]\s?moc|plnou\s?moc|power\s?of\s?attorney': "poa",
    r'апостил|apostil': "apostille",
    r'заяв|згод|согласи|prohlášen|prohlasen|souhlas|statement|consent': "statement",
    r'несудим|trest|rejstřík|rejstrik|police\s?clearance|criminal': "police_clearance",
    r'одруж|брак|шлюб|свадьб|sňatk|snatk|svatb|marriag|weddin': "marriage",
    r'дублікат|дубликат|duplikát|duplikat|duplicat': "duplicates",
}
```

(Dict insertion order matters here — `FormValidator.detect_service` returns on first regex match, so `legal_consultation`/`visa_consultation` must be checked before the generic `consultation_ambiguous` pattern, which this ordering already satisfies.)

- [ ] **Step 4: Update `SERVICE_LOCALIZED_NAMES`**

Find (lines 50-59):

```python
SERVICE_LOCALIZED_NAMES = {
    "consultation": {"uk": "Консультації", "ru": "Консультации", "cs": "Konzultace", "en": "Consultations"},
    "translation": {"uk": "Судові переклади", "ru": "Судебные переводы", "cs": "Soudní překlady", "en": "Sworn Translations"},
```

Replace the first line with two entries:

```python
SERVICE_LOCALIZED_NAMES = {
    "legal_consultation": {"uk": "Юридичні консультації", "ru": "Юридические консультации", "cs": "Právní konzultace", "en": "Legal Consultations"},
    "visa_consultation": {"uk": "Візові консультації", "ru": "Визовые консультации", "cs": "Vízové konzultace", "en": "Visa Consultations"},
    "translation": {"uk": "Судові переклади", "ru": "Судебные переводы", "cs": "Soudní překlady", "en": "Sworn Translations"},
```

(Leave every other entry in this dict untouched.)

- [ ] **Step 5: Add the three new copy dicts**

Insert immediately after `EMAIL_REPROMPT`'s closing `}` (currently ends at line 175, right before `SERVICES_LIST_RESPONSE`):

```python
CONSULTATION_TYPE_PROMPT = {
    "en": "Would you like a **Legal Consultation** or a **Visa/Migration Consultation**?",
    "cs": "Chcete **právní konzultaci**, nebo **vízovou/migrační konzultaci**?",
    "uk": "Вас цікавить **юридична консультація** чи **візова/міграційна консультація**?",
    "ru": "Вас интересует **юридическая консультация** или **визовая/миграционная консультация**?",
}

CONTACT_CONFIRMATION_PROMPT = {
    "en": "Would you like our manager to contact you to arrange this? **Yes** — please leave your name and phone number, or **No**.",
    "cs": "Přejete si, aby vás kontaktoval náš manažer kvůli vyřízení tohoto požadavku? **Ano** — uveďte prosím své jméno a telefonní číslo, nebo **Ne**.",
    "uk": "Чи бажаєте, щоб з Вами зв'язався наш менеджер для оформлення запиту? **Так** — залиште, будь ласка, Ваше ім'я та номер телефону, або **Ні**.",
    "ru": "Хотите, чтобы с Вами связался наш менеджер для оформления запроса? **Да** — оставьте, пожалуйста, Ваше имя и номер телефона, или **Нет**.",
}

CONTACT_DECLINED_MESSAGE = {
    "en": "No problem at all! Feel free to reach out anytime if you have questions. 😊",
    "cs": "Žádný problém! Pokud budete mít jakékoli dotazy, neváhejte se kdykoli ozvat. 😊",
    "uk": "Добре, немає проблем! Якщо виникнуть питання — звертайтесь у будь-який час. 😊",
    "ru": "Хорошо, никаких проблем! Если возникнут вопросы — обращайтесь в любое время. 😊",
}
```

- [ ] **Step 6: Tighten `WHEN_WILL_YOU_CALL_RESPONSE["uk"]`**

The client's requested wording is almost identical to what's already there — the only real difference is a missing "годинами" (hours) at the end (their message was also missing "з" before "понеділка", but the current text already has it correctly — no change needed there). Find (line 185):

```python
    "uk": "З Вами зв'яжуться в найкоротші строки під час нашого робочого дня з понеділка по п'ятницю між 8:00 та 17:00.",
```

Replace with:

```python
    "uk": "З Вами зв'яжуться в найкоротші строки під час нашого робочого дня з понеділка по п'ятницю між 8:00 та 17:00 годинами.",
```

- [ ] **Step 7: Run test to verify it passes**

Run: `poetry run pytest tests/test_service_patterns.py -v`
Expected: PASS (4 tests)

- [ ] **Step 8: Run the full suite**

Run: `poetry run pytest -v`
Expected: all existing tests still pass — check specifically for any test asserting on the old `"consultation"` service ID or `SERVICE_LOCALIZED_NAMES["consultation"]`; none exist today (confirmed: no test file references `SERVICE_PATTERNS`, `SERVICE_LOCALIZED_NAMES`, or a `"consultation"` service ID before this plan), so no other test should break.

- [ ] **Step 9: Commit**

```bash
git add src/ai/conversation_agent/agent_rules/strings.py tests/test_service_patterns.py
git commit -m "feat: split conflated consultation service pattern, add new lead-flow copy"
```

---

### Task 2: Shared affirmative/negative word matching

**Files:**
- Create: `src/ai/conversation_agent/agent_rules/affirmation.py`
- Modify: `src/ai/conversation_agent/nodes/gate.py`
- Test: `tests/test_affirmation.py`

**Interfaces:**
- Produces: `is_affirmative(text: str) -> bool`, `is_negative(text: str) -> bool` — consumed by `gate.py` (this task) and by Task 3's new `_step_awaiting_contact_confirmation`.

This is a pure extraction — `gate.py`'s existing `_AFFIRMATIVE_WORDS` set and matching logic move into the new shared module unchanged in content; `is_affirmative_reply_to_manager_prompt`'s behavior does not change.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_affirmation.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_affirmation.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ai.conversation_agent.agent_rules.affirmation'`

- [ ] **Step 3: Write `agent_rules/affirmation.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/test_affirmation.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Refactor `gate.py` to use the shared helper**

Find (lines 15-19 and 45-53):

```python
_AFFIRMATIVE_WORDS = {"ano", "yes", "так", "да", "chci", "y"}
_MANAGER_PROMPT_MARKERS = [
    "(ano / ne)", "(yes / no)", "(так / ні)", "(да / нет)",
    "kontaktoval", "contact", "зв'яжеться", "свяжется", "contact you",
]
```

Replace with:

```python
_MANAGER_PROMPT_MARKERS = [
    "(ano / ne)", "(yes / no)", "(так / ні)", "(да / нет)",
    "kontaktoval", "contact", "зв'яжеться", "свяжется", "contact you",
]
```

Find (lines 45-53):

```python
def is_affirmative_reply_to_manager_prompt(text: str, history: list[dict]) -> bool:
    """True if the bot's last message asked "want us to contact you?" and
    this reply is a bare "yes"-shaped answer - short-circuits the LLM call
    for this very common, very unambiguous turn."""
    text_lower = text.lower().strip()
    last_bot_msg = _last_bot_message(history)
    if not any(marker in last_bot_msg for marker in _MANAGER_PROMPT_MARKERS):
        return False
    return text_lower == "a" or any(text_lower.startswith(w) for w in _AFFIRMATIVE_WORDS)
```

Replace with:

```python
def is_affirmative_reply_to_manager_prompt(text: str, history: list[dict]) -> bool:
    """True if the bot's last message asked "want us to contact you?" and
    this reply is a bare "yes"-shaped answer - short-circuits the LLM call
    for this very common, very unambiguous turn."""
    last_bot_msg = _last_bot_message(history)
    if not any(marker in last_bot_msg for marker in _MANAGER_PROMPT_MARKERS):
        return False
    return is_affirmative(text)
```

Add the import at the top of the file (alongside the existing imports):

```python
from src.ai.conversation_agent.agent_rules.affirmation import is_affirmative
```

- [ ] **Step 6: Run gate tests to verify no regression**

Run: `poetry run pytest tests/test_gate.py -v`
Expected: PASS (10 tests, unchanged — `is_affirmative_reply_to_manager_prompt`'s behavior is identical, just delegates internally now)

- [ ] **Step 7: Run the full suite**

Run: `poetry run pytest -v`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add src/ai/conversation_agent/agent_rules/affirmation.py src/ai/conversation_agent/nodes/gate.py tests/test_affirmation.py
git commit -m "refactor: extract shared affirmative/negative word matching"
```

---

### Task 3: New `lead_capture` steps

**Files:**
- Modify: `src/ai/conversation_agent/state.py`
- Modify: `src/ai/conversation_agent/nodes/lead_capture.py`
- Test: `tests/test_lead_capture_flow.py` (new)

**Interfaces:**
- Consumes: `CONSULTATION_TYPE_PROMPT`/`CONTACT_CONFIRMATION_PROMPT`/`CONTACT_DECLINED_MESSAGE` (Task 1), `is_affirmative`/`is_negative` (Task 2).
- Produces: two new `lead_step` values (`"awaiting_consultation_type"`, `"awaiting_contact_confirmation"`) in the state machine — no change to `AgentState`'s schema (`lead_step` is already a free-form-enough field; check `state.py` — if it's a `Literal[...]` type, it needs the two new values added, see Step 0 below).

- [ ] **Step 0: Add the two new step names to `AgentState.lead_step`'s `Literal` type**

Confirmed: `src/ai/conversation_agent/state.py:22` currently reads:

```python
    lead_step: Literal["awaiting_service", "awaiting_name", "awaiting_phone", "awaiting_email", "completed"] | None = None
```

Pydantic rejects any string not in this `Literal` on assignment — every new step in this task would fail validation without this change. Replace with:

```python
    lead_step: Literal["awaiting_service", "awaiting_consultation_type", "awaiting_contact_confirmation", "awaiting_name", "awaiting_phone", "awaiting_email", "completed"] | None = None
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_lead_capture_flow.py
from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.ai.conversation_agent.nodes.lead_capture import (
    _step_start,
    _step_awaiting_service,
    _step_awaiting_consultation_type,
    _step_awaiting_contact_confirmation,
)
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState
from src.schemas.ai.messages import IncomingMessage


def _incoming(text):
    return IncomingMessage(
        client_id="1", channel="telegram", text=text,
        timestamp=datetime.now(), client_name="Test",
    )


def _state(text, history=None, language="uk", **kwargs):
    return AgentState(
        incoming=_incoming(text),
        conversation_history=history or [],
        language=language,
        **kwargs,
    )


# --- _step_start: ambiguous consultation ---

async def test_step_start_ambiguous_consultation_asks_which_type():
    state = _state("потрібна консультація")
    result = await _step_start(state)
    assert result["lead_step"] == "awaiting_consultation_type"
    assert "юридична" in result["response"].lower() or "візова" in result["response"].lower()


# --- _step_start: concrete service, price not yet shown ---

async def test_step_start_concrete_service_no_price_hands_to_chat():
    state = _state("потрібен юрист")
    result = await _step_start(state)
    assert result.get("route_to_llm") is True
    assert result["current_service"] == "legal_consultation"


# --- _step_start: concrete service, price already shown ---

async def test_step_start_concrete_service_price_shown_asks_confirmation():
    history = [{"role": "assistant", "content": "Consultation costs 1900 CZK"}]
    state = _state("потрібен юрист", history=history)
    result = await _step_start(state)
    assert result["lead_step"] == "awaiting_contact_confirmation"
    assert result["current_service"] == "legal_consultation"


# --- _step_awaiting_service: price shown now goes to confirmation, not name ---

async def test_step_awaiting_service_price_shown_lands_on_confirmation_not_name():
    history = [{"role": "assistant", "content": "Apostille costs 4000 CZK"}]
    state = _state("апостиль", history=history)
    result = await _step_awaiting_service(state)
    assert result["lead_step"] == "awaiting_contact_confirmation"
    assert result["current_service"] == "apostille"


# --- _step_awaiting_consultation_type ---

async def test_step_awaiting_consultation_type_resolves_legal():
    state = _state("юридична", lead_step="awaiting_consultation_type")
    result = await _step_awaiting_consultation_type(state)
    assert result["current_service"] == "legal_consultation"


async def test_step_awaiting_consultation_type_resolves_visa():
    state = _state("візова", lead_step="awaiting_consultation_type")
    result = await _step_awaiting_consultation_type(state)
    assert result["current_service"] == "visa_consultation"


async def test_step_awaiting_consultation_type_reprompts_when_still_unclear():
    state = _state("не знаю", lead_step="awaiting_consultation_type")
    with patch(
        "src.ai.conversation_agent.nodes.lead_capture.FormValidator.is_user_asking_question",
        new_callable=AsyncMock, return_value=False,
    ):
        result = await _step_awaiting_consultation_type(state)
    assert result.get("lead_step") is None  # unchanged (reprompt) - caller keeps current step
    assert "юридична" in result["response"].lower() or "візова" in result["response"].lower()


async def test_step_awaiting_consultation_type_hands_off_on_question():
    state = _state("скільки це коштує?", lead_step="awaiting_consultation_type")
    with patch(
        "src.ai.conversation_agent.nodes.lead_capture.FormValidator.is_user_asking_question",
        new_callable=AsyncMock, return_value=True,
    ):
        result = await _step_awaiting_consultation_type(state)
    assert result.get("route_to_llm") is True


# --- _step_awaiting_contact_confirmation ---

async def test_step_awaiting_contact_confirmation_yes_advances_to_name():
    state = _state("так", lead_step="awaiting_contact_confirmation", current_service="apostille")
    result = await _step_awaiting_contact_confirmation(state)
    assert result["lead_step"] == "awaiting_name"
    assert result["route"] == Route.LEAD


async def test_step_awaiting_contact_confirmation_no_resets_and_declines():
    state = _state(
        "ні", lead_step="awaiting_contact_confirmation", current_service="apostille",
        client_name="should be cleared",
    )
    result = await _step_awaiting_contact_confirmation(state)
    assert result["lead_step"] is None
    assert result["current_service"] is None
    assert result["client_name"] is None


async def test_step_awaiting_contact_confirmation_question_hands_off():
    state = _state("а скільки коштує?", lead_step="awaiting_contact_confirmation", current_service="apostille")
    with patch(
        "src.ai.conversation_agent.nodes.lead_capture.FormValidator.is_user_asking_question",
        new_callable=AsyncMock, return_value=True,
    ):
        result = await _step_awaiting_contact_confirmation(state)
    assert result.get("route_to_llm") is True


async def test_step_awaiting_contact_confirmation_unclear_reprompts():
    state = _state("хм", lead_step="awaiting_contact_confirmation", current_service="apostille")
    with patch(
        "src.ai.conversation_agent.nodes.lead_capture.FormValidator.is_user_asking_question",
        new_callable=AsyncMock, return_value=False,
    ):
        result = await _step_awaiting_contact_confirmation(state)
    assert result.get("lead_step") is None  # unchanged, caller keeps current step
    assert result.get("route_to_llm") is not True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_lead_capture_flow.py -v`
Expected: FAIL — `ImportError: cannot import name '_step_awaiting_consultation_type'` (functions don't exist yet).

- [ ] **Step 3: Add the new imports to `lead_capture.py`**

Find (lines 10-19):

```python
from src.ai.conversation_agent.agent_rules.strings import (
    MESSAGES,
    WEEKEND_NOTICES,
    PHONE_REPROMPT,
    NAME_REPROMPT,
    EMAIL_REPROMPT,
    SERVICES_LIST_RESPONSE,
    WHEN_WILL_YOU_CALL_RESPONSE,
    SERVICE_LOCALIZED_NAMES,
)
from src.ai.conversation_agent.agent_rules.form_validator import FormValidator
```

Replace with:

```python
from src.ai.conversation_agent.agent_rules.strings import (
    MESSAGES,
    WEEKEND_NOTICES,
    PHONE_REPROMPT,
    NAME_REPROMPT,
    EMAIL_REPROMPT,
    SERVICES_LIST_RESPONSE,
    WHEN_WILL_YOU_CALL_RESPONSE,
    SERVICE_LOCALIZED_NAMES,
    CONSULTATION_TYPE_PROMPT,
    CONTACT_CONFIRMATION_PROMPT,
    CONTACT_DECLINED_MESSAGE,
)
from src.ai.conversation_agent.agent_rules.form_validator import FormValidator
from src.ai.conversation_agent.agent_rules.affirmation import is_affirmative, is_negative
```

(`WEEKEND_NOTICES` was already imported but unused before this plan — Task 4 wires it up; leave the import as-is here.)

- [ ] **Step 4: Update `_check_question_trap`'s handled-steps tuple**

Find (line 63-64):

```python
async def _check_question_trap(state: AgentState, step: Optional[str]) -> Optional[dict]:
    if step not in ("awaiting_name", "awaiting_phone", "awaiting_email"):
```

Replace with:

```python
async def _check_question_trap(state: AgentState, step: Optional[str]) -> Optional[dict]:
    if step not in (
        "awaiting_name", "awaiting_phone", "awaiting_email",
        "awaiting_consultation_type", "awaiting_contact_confirmation",
    ):
```

- [ ] **Step 5: Rewrite `_step_start`**

Find (lines 84-112):

```python
async def _step_start(state: AgentState) -> dict:
    service = (
        state.current_service
        or FormValidator.extract_service_from_history(
            state.conversation_history,
            current_text=state.incoming.text,
        )
        or FormValidator.detect_service(state.incoming.text)
    )

    if not service:
        return {
            "lead_step": "awaiting_service",
            "route_to_llm": False,
            "response": SERVICES_LIST_RESPONSE.get(
                state.language,
                SERVICES_LIST_RESPONSE["en"],
            ),
        }

    return {
        "current_service": service,
        "lead_step": "awaiting_name",
        "route_to_llm": False,
        "response": _service_reprompt(
            service,
            state.language,
        ),
    }
```

Replace with:

```python
async def _step_start(state: AgentState) -> dict:
    service = (
        state.current_service
        or FormValidator.extract_service_from_history(
            state.conversation_history,
            current_text=state.incoming.text,
        )
        or FormValidator.detect_service(state.incoming.text)
    )

    if not service:
        return {
            "lead_step": "awaiting_service",
            "route_to_llm": False,
            "response": SERVICES_LIST_RESPONSE.get(
                state.language,
                SERVICES_LIST_RESPONSE["en"],
            ),
        }

    if service == "consultation_ambiguous":
        return {
            "lead_step": "awaiting_consultation_type",
            "route_to_llm": False,
            "response": CONSULTATION_TYPE_PROMPT.get(
                state.language,
                CONSULTATION_TYPE_PROMPT["en"],
            ),
        }

    if not FormValidator.has_price_been_shown(state.conversation_history):
        return {"route_to_llm": True, "current_service": service}

    return {
        "current_service": service,
        "lead_step": "awaiting_contact_confirmation",
        "route_to_llm": False,
        "response": CONTACT_CONFIRMATION_PROMPT.get(
            state.language,
            CONTACT_CONFIRMATION_PROMPT["en"],
        ),
    }
```

- [ ] **Step 6: Update `_step_awaiting_service`**

Find (lines 114-126):

```python
async def _step_awaiting_service(state: AgentState) -> dict:
    detected_id = FormValidator.detect_service(state.incoming.text)
    if not detected_id:
        return {"route_to_llm": True, "lead_step": None}

    if not FormValidator.has_price_been_shown(state.conversation_history):
        return {"route_to_llm": True, "current_service": detected_id}

    return {
        "current_service": detected_id,
        "lead_step": "awaiting_name",
        "response": _service_reprompt(detected_id, state.language),
    }
```

Replace with:

```python
async def _step_awaiting_service(state: AgentState) -> dict:
    detected_id = FormValidator.detect_service(state.incoming.text)
    if not detected_id:
        return {"route_to_llm": True, "lead_step": None}

    if detected_id == "consultation_ambiguous":
        return {
            "lead_step": "awaiting_consultation_type",
            "response": CONSULTATION_TYPE_PROMPT.get(
                state.language,
                CONSULTATION_TYPE_PROMPT["en"],
            ),
        }

    if not FormValidator.has_price_been_shown(state.conversation_history):
        return {"route_to_llm": True, "current_service": detected_id}

    return {
        "current_service": detected_id,
        "lead_step": "awaiting_contact_confirmation",
        "response": CONTACT_CONFIRMATION_PROMPT.get(
            state.language,
            CONTACT_CONFIRMATION_PROMPT["en"],
        ),
    }
```

- [ ] **Step 7: Add the two new step handlers**

Insert immediately before `_step_awaiting_name` (after `_step_awaiting_service`'s new closing brace):

```python
async def _step_awaiting_consultation_type(state: AgentState) -> dict:
    detected_id = FormValidator.detect_service(state.incoming.text)

    if detected_id in ("legal_consultation", "visa_consultation"):
        if not FormValidator.has_price_been_shown(state.conversation_history):
            return {"route_to_llm": True, "current_service": detected_id}
        return {
            "current_service": detected_id,
            "lead_step": "awaiting_contact_confirmation",
            "response": CONTACT_CONFIRMATION_PROMPT.get(
                state.language,
                CONTACT_CONFIRMATION_PROMPT["en"],
            ),
        }

    if await FormValidator.is_user_asking_question(state.incoming.text):
        return {"route_to_llm": True}

    # Still ambiguous or unrelated - reprompt the same question, step unchanged.
    return {
        "response": CONSULTATION_TYPE_PROMPT.get(
            state.language,
            CONSULTATION_TYPE_PROMPT["en"],
        ),
    }


async def _step_awaiting_contact_confirmation(state: AgentState) -> dict:
    text = state.incoming.text.strip()

    if is_affirmative(text):
        msg = MESSAGES.get(state.language, MESSAGES["uk"])
        return {
            "lead_step": "awaiting_name",
            "route": Route.LEAD,
            "response": msg["start"],
        }

    if is_negative(text):
        return {
            **_RESET_FIELDS,
            "response": CONTACT_DECLINED_MESSAGE.get(
                state.language,
                CONTACT_DECLINED_MESSAGE["en"],
            ),
        }

    if await FormValidator.is_user_asking_question(text):
        return {"route_to_llm": True}

    # Neither yes, no, nor a question - reprompt the same gate, step unchanged.
    return {
        "response": CONTACT_CONFIRMATION_PROMPT.get(
            state.language,
            CONTACT_CONFIRMATION_PROMPT["en"],
        ),
    }
```

- [ ] **Step 8: Update `_STEP_HANDLERS`**

Find (lines 235-242, after the two new handlers are added above — line numbers will have shifted, locate by content instead):

```python
_STEP_HANDLERS = {
    None: _step_start,
    "start": _step_start,
    "awaiting_service": _step_awaiting_service,
    "awaiting_name": _step_awaiting_name,
    "awaiting_phone": _step_awaiting_phone,
    "awaiting_email": _step_awaiting_email,
}
```

Replace with:

```python
_STEP_HANDLERS = {
    None: _step_start,
    "start": _step_start,
    "awaiting_service": _step_awaiting_service,
    "awaiting_consultation_type": _step_awaiting_consultation_type,
    "awaiting_contact_confirmation": _step_awaiting_contact_confirmation,
    "awaiting_name": _step_awaiting_name,
    "awaiting_phone": _step_awaiting_phone,
    "awaiting_email": _step_awaiting_email,
}
```

- [ ] **Step 9: Run the new tests**

Run: `poetry run pytest tests/test_lead_capture_flow.py -v`
Expected: PASS (11 tests)

- [ ] **Step 10: Run the full suite**

Run: `poetry run pytest -v`
Expected: all pass — `tests/test_lead_capture.py`'s existing 4 tests exercise `_step_awaiting_email` directly and are unaffected by everything in this task (which only touches code before `awaiting_name`).

- [ ] **Step 11: Commit**

```bash
git add src/ai/conversation_agent/state.py src/ai/conversation_agent/nodes/lead_capture.py tests/test_lead_capture_flow.py
git commit -m "feat: consultation-type disambiguation and contact-confirmation gate before collecting contact details"
```

---

### Task 4: Universal call-timing fast-path + weekend wiring

**Files:**
- Modify: `src/ai/conversation_agent/nodes/chat.py`
- Modify: `src/ai/conversation_agent/nodes/lead_capture.py`
- Test: `tests/test_chat.py` (append)
- Test: `tests/test_lead_capture_flow.py` (append)

**Interfaces:**
- Consumes: `FormValidator.is_asking_call_timing`, `FormValidator.has_weekend_mention` (both already exist, unchanged), `WHEN_WILL_YOU_CALL_RESPONSE`, `WEEKEND_NOTICES` (Task 1's tightened `uk` entry).
- Produces: `chat_node` now short-circuits call-timing questions before any LLM call, regardless of `lead_step`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_chat.py`:

```python
async def test_chat_call_timing_fast_path_skips_llm(tmp_path):
    info_file = tmp_path / "company_info.md"
    info_file.write_text("## English (en)\nWe offer legal consultations.", encoding="utf-8")
    with patch(
        "src.ai.conversation_agent.nodes.chat.get_llm"
    ) as get_llm, patch(
        "src.ai.conversation_agent.nodes.chat.settings"
    ) as mock_settings:
        mock_settings.company_info_path = str(info_file)
        mock_settings.llm_model = "gpt-4o-mini"
        result = await chat_node(_state("коли ви зателефонуєте?", language="uk"))
    get_llm.assert_not_called()
    assert "8:00" in result["response"] and "17:00" in result["response"]


async def test_chat_call_timing_fast_path_prepends_weekend_notice(tmp_path):
    info_file = tmp_path / "company_info.md"
    info_file.write_text("## English (en)\nWe offer legal consultations.", encoding="utf-8")
    with patch(
        "src.ai.conversation_agent.nodes.chat.get_llm"
    ), patch(
        "src.ai.conversation_agent.nodes.chat.settings"
    ) as mock_settings:
        mock_settings.company_info_path = str(info_file)
        mock_settings.llm_model = "gpt-4o-mini"
        result = await chat_node(_state("зателефонуйте мені в суботу", language="uk"))
    assert "вихідн" in result["response"].lower()
    assert "8:00" in result["response"]


async def test_chat_non_call_timing_message_still_uses_llm(tmp_path):
    info_file = tmp_path / "company_info.md"
    info_file.write_text("## English (en)\nWe offer legal consultations.", encoding="utf-8")
    reply = AIMessage(content="hi there", tool_calls=[])
    with patch(
        "src.ai.conversation_agent.nodes.chat.get_llm", return_value=_fake_llm(reply)
    ), patch(
        "src.ai.conversation_agent.nodes.chat.settings"
    ) as mock_settings:
        mock_settings.company_info_path = str(info_file)
        mock_settings.llm_model = "gpt-4o-mini"
        result = await chat_node(_state("Привіт", language="uk"))
    assert result == {"response": "hi there"}
```

(These reuse `_state`/`_fake_llm`/`AIMessage`/`patch` already imported at the top of `tests/test_chat.py` — no new imports needed there.)

Append to `tests/test_lead_capture_flow.py`:

```python
def test_check_call_timing_prepends_weekend_notice_mid_form():
    import asyncio
    from src.ai.conversation_agent.nodes.lead_capture import _check_call_timing

    state = _state("зателефонуйте мені в суботу", language="uk", lead_step="awaiting_name")
    result = asyncio.run(_check_call_timing(state, "awaiting_name"))
    assert result is not None
    assert "вихідн" in result["response"].lower()
    assert "8:00" in result["response"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_chat.py::test_chat_call_timing_fast_path_skips_llm -v`
Expected: FAIL — `get_llm.assert_not_called()` fails, since `chat_node` doesn't have this fast-path yet and calls the (mocked) LLM regardless.

- [ ] **Step 3: Add the fast-path to `chat_node`**

Find (`nodes/chat.py`, the full current file):

```python
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.ai.conversation_agent.prompts.chat import SYSTEM_PROMPT
from src.ai.conversation_agent.prompts.handoff import HANDOFF_MESSAGES
from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.tools.chat_tools import build_log_unanswered_question_tool
from src.ai.llm import get_llm
from src.config import settings
from src.logger import log_event
```

Replace with:

```python
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.ai.conversation_agent.agent_rules.form_validator import FormValidator
from src.ai.conversation_agent.agent_rules.strings import WEEKEND_NOTICES, WHEN_WILL_YOU_CALL_RESPONSE
from src.ai.conversation_agent.prompts.chat import SYSTEM_PROMPT
from src.ai.conversation_agent.prompts.handoff import HANDOFF_MESSAGES
from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.tools.chat_tools import build_log_unanswered_question_tool
from src.ai.llm import get_llm
from src.config import settings
from src.logger import log_event
```

Find:

```python
async def chat_node(state: AgentState) -> dict:
    """One conversational node replacing the old info/off_topic/escalation
    split: FAQ answering, identity, off-topic redirects, and human handoff
    for unanswerable-but-relevant questions all live here now, grounded
    entirely in src/assets/company_info.md rather than retrieval."""
    lang = state.language or "uk"
    log_unanswered_question = build_log_unanswered_question_tool(
        conversation_id=state.conversation_id
    )
```

Replace with:

```python
async def chat_node(state: AgentState) -> dict:
    """One conversational node replacing the old info/off_topic/escalation
    split: FAQ answering, identity, off-topic redirects, and human handoff
    for unanswerable-but-relevant questions all live here now, grounded
    entirely in src/assets/company_info.md rather than retrieval."""
    lang = state.language or "uk"

    # Fast-path, mirrors lead_capture.py's _check_call_timing: this used to
    # only have exact-wording guarantees inside an active lead form (the
    # standalone node that handled it everywhere else was removed in the
    # 2026-08-26 graph refactor - an unintentional gap, not a deliberate
    # decision). No LLM call needed for this one.
    if FormValidator.is_asking_call_timing(state.incoming.text):
        response = WHEN_WILL_YOU_CALL_RESPONSE.get(lang, WHEN_WILL_YOU_CALL_RESPONSE["en"])
        if FormValidator.has_weekend_mention(state.incoming.text):
            response = WEEKEND_NOTICES.get(lang, WEEKEND_NOTICES["en"]) + response
        return {"response": response}

    log_unanswered_question = build_log_unanswered_question_tool(
        conversation_id=state.conversation_id
    )
```

- [ ] **Step 4: Wire the same weekend prepend into `lead_capture.py`'s `_check_call_timing`**

Find (`nodes/lead_capture.py`):

```python
async def _check_call_timing(state: AgentState, step: Optional[str]) -> Optional[dict]:
    if not FormValidator.is_asking_call_timing(state.incoming.text):
        return None
    return {
        "route_to_llm": False,
        "response": WHEN_WILL_YOU_CALL_RESPONSE.get(state.language, WHEN_WILL_YOU_CALL_RESPONSE["en"]),
    }
```

Replace with:

```python
async def _check_call_timing(state: AgentState, step: Optional[str]) -> Optional[dict]:
    if not FormValidator.is_asking_call_timing(state.incoming.text):
        return None
    response = WHEN_WILL_YOU_CALL_RESPONSE.get(state.language, WHEN_WILL_YOU_CALL_RESPONSE["en"])
    if FormValidator.has_weekend_mention(state.incoming.text):
        response = WEEKEND_NOTICES.get(state.language, WEEKEND_NOTICES["en"]) + response
    return {
        "route_to_llm": False,
        "response": response,
    }
```

- [ ] **Step 5: Run the new tests**

Run: `poetry run pytest tests/test_chat.py tests/test_lead_capture_flow.py -v`
Expected: PASS (all, including the 4 new ones from this task)

- [ ] **Step 6: Run the full suite**

Run: `poetry run pytest -v`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add src/ai/conversation_agent/nodes/chat.py src/ai/conversation_agent/nodes/lead_capture.py tests/test_chat.py tests/test_lead_capture_flow.py
git commit -m "feat: universal call-timing fast-path with weekend notice, wired into chat and lead_capture"
```

---

### Task 5: Update `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Update the `lead_capture` bullet in "The conversation graph"**

Read the current `- **\`lead_capture\`**` bullet in `CLAUDE.md`'s "### The conversation graph" section. Extend its description of the state machine to mention the two new steps and the pre-name-collection sequence, e.g. (adapt to whatever the bullet's current exact wording is — don't blind-replace without reading it first, it's been edited several times today):

> `nodes/lead_capture.py` — unchanged in spirit, but the pre-name-collection sequence was redesigned 2026-08-27 after real client feedback: a detected service now goes through `awaiting_consultation_type` (only for an ambiguous bare "consultation" — disambiguates legal vs. visa/migration) and `awaiting_contact_confirmation` (a universal yes/no gate, entered once pricing has been shown via `FormValidator.has_price_been_shown`) before ever reaching `awaiting_name`. A "no" at the confirmation gate resets the form without collecting any personal data.

- [ ] **Step 2: Add a note about the call-timing fast-path**

In the `chat` bullet (or wherever `chat_node` is described), add a sentence noting the call-timing fast-path added in this plan, e.g.: "Also fast-paths the exact-wording 'when will you call me?' response (with a weekend-mention special case) before any LLM call — this used to only be guaranteed inside an active lead form; reinstated everywhere 2026-08-27."

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for the redesigned lead-capture flow"
```

## Explicitly out of scope for this plan

- `chat`'s own free-text pricing explanation (when a service is detected but pricing hasn't been shown yet, `_step_start`/`_step_awaiting_service`/`_step_awaiting_consultation_type` all hand off to `chat` with `route_to_llm=True`) remains LLM-generated prose. Its content quality is a prompt-engineering concern (already partially addressed by the "list every variant" fix from 2026-08-26), not something this plan changes or can unit-test.
- Everything from `awaiting_name` onward (name/phone/email collection, validation, the completion notification) — untouched.
- `_SKIP_EMAIL_WORDS` and the email-skip flow — untouched, deliberately kept separate from the new yes/no gate (see Global Constraints).
