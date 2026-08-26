# Lead Capture Flow Redesign — Design Spec

## Background

Real client feedback (relayed 2026-08-26) on a live production test: asking "потрібна консультація" (I need a consultation) caused the bot to jump straight to asking for the client's name, without ever clarifying whether they wanted a legal or visa/migration consultation, without showing pricing, and without explicitly asking permission before starting to collect contact details.

Root causes, confirmed against the current code:

1. **`SERVICE_PATTERNS`** (`agent_rules/strings.py`) has a single `"consultation"` entry whose regex conflates legal-specific terms (`юрист`, `advokát`, `lawyer`, `адвокат`) and visa-specific terms (`віз`, `виз`, `visa`) into one service ID. A bare "консультація" matches it immediately — there is no way for the system to know which type was meant.
2. **`_step_start`** (`nodes/lead_capture.py`) detects a service on the client's very first message and jumps straight to `lead_step="awaiting_name"`, skipping the `has_price_been_shown` gate that `_step_awaiting_service` already correctly implements for the *other* entry path (when the service isn't known until a follow-up message). This inconsistency is why pricing wasn't shown before the client was asked for their name.
3. There has never been an explicit "do you want to be contacted?" yes/no question — providing a name has always been treated as tacit confirmation.
4. **`WEEKEND_NOTICES`** and **`FormValidator.has_weekend_mention`** are fully implemented but have zero callers anywhere in the codebase — dead code.
5. The exact-wording "when will you call me?" response (`WHEN_WILL_YOU_CALL_RESPONSE`) only fires inside an active lead form (`lead_capture.py`'s `_check_call_timing` intercept). The standalone node that used to handle this question outside a form was removed during the 2026-08-26 graph refactor (`docs/superpowers/plans/2026-08-26-conversational-graph-refactor.md`) — an unintentional gap, not a deliberate decision.

## Goals

- Every service (not just consultations) follows the same sequence: clarify what's needed → show pricing → explicitly ask permission to collect contact details → only then collect name/phone/email.
- Legal vs. visa/migration consultations are distinguished, with a natural clarifying question when the client's message is ambiguous.
- The manager-contact yes/no question is a real, deterministic gate — a "no" cleanly ends the funnel without collecting any personal data.
- "When will you call me?" gets the exact requested wording, including the weekend special-case, regardless of when in the conversation it's asked.

## Non-goals

- Changing how `gate` decides `wants_lead` in the first place (unchanged — still an LLM classification of the *first* message in a new conversation).
- Changing anything about phone/email validation, or the `chat` node's own tool-based FAQ answering.
- A full audit of every dead-code path in the codebase — only the two (`WEEKEND_NOTICES`, `has_weekend_mention`) directly relevant to this flow.

## Design

### 1. Flow shape

```
User message
  │
  ▼
gate ──(call-timing question, regardless of lead_step)──► deterministic exact-wording answer, turn ends
  │
  ├─(wants_lead=False)──► chat (unchanged: FAQ/pricing/identity, grounded in company_info.md)
  │
  └─(wants_lead=True)──► lead_capture
                            │
                            ▼
                       service detected?
                        │           │
                       no          yes
                        │           │
                 show services   ambiguous "consultation"
                 list, wait      (no legal/visa qualifier)?
                                   │            │
                                  yes           no
                                   │            │
                          ask Legal/Visa    has price been
                          (2 options)       shown yet?
                                              │        │
                                             no        yes
                                              │         │
                                        hand to chat   ask "Contact
                                        (shows price)   you? Yes/No"
                                                          │      │
                                                         yes     no
                                                          │      │
                                                    awaiting_name  polite
                                                    → phone → email  close,
                                                    → notify manager  form resets
```

### 2. Service detection & disambiguation

**`SERVICE_PATTERNS`** (`src/ai/conversation_agent/agent_rules/strings.py`): replace the single `"consultation"` entry with three, checked in this order (regex dict iteration order in `FormValidator.detect_service` must check the more specific two before the generic one — see implementation note below):

```python
SERVICE_PATTERNS = {
    r'юрист|правнич|legal\s?consult|právní\s?konzult|advokát|advokat|lawyer|адвокат': "legal_consultation",
    r'віз[аиу]|виз[аыу]|migra|vízov|migrant': "visa_consultation",
    r'кон[сзм][уь]?ль?т|konzultac|consult': "consultation_ambiguous",
    r'переклад|перевод|překlad|preklad|translat': "translation",
    r'довір|довер|pln[aeáé]\s?moc|plnou\s?moc|power\s?of\s?attorney': "poa",
    r'апостил|apostil': "apostille",
    r'заяв|згод|согласи|prohlášen|prohlasen|souhlas|statement|consent': "statement",
    r'несудим|trest|rejstřík|rejstrik|police\s?clearance|criminal': "police_clearance",
    r'одруж|брак|шлюб|свадьб|sňatk|snatk|svatb|marriag|weddin': "marriage",
    r'дублікат|дубликат|duplikát|duplikat|duplicat': "duplicates",
}
```

**Implementation note:** `FormValidator.detect_service` iterates `SERVICE_PATTERNS.items()` and returns on first match — Python dicts preserve insertion order, so placing `legal_consultation`/`visa_consultation` before `consultation_ambiguous` in the dict literal is sufficient; no other change to `detect_service`'s logic is needed. A message containing both a legal and visa term (unlikely, but possible) matches whichever pattern is checked first — `legal_consultation`, arbitrarily; not worth special-casing.

`consultation_ambiguous` is a sentinel, not a real bookable service — `_step_start`/`_step_awaiting_service` (see below) special-case it to show the clarifying question instead of proceeding to pricing.

**`SERVICE_LOCALIZED_NAMES`** gains two new entries for `legal_consultation`/`visa_consultation` (reuse the existing `"consultation"` entry's text for `legal_consultation` since that's what "Consultations" already meant in practice; add matching visa-specific localized names). The old bare `"consultation"` key is removed since nothing produces that ID anymore.

**New copy** — `CONSULTATION_TYPE_PROMPT` (new dict in `agent_rules/strings.py`, 4 languages, same style as `SERVICES_LIST_RESPONSE`):

> en: "Would you like a **Legal Consultation** or a **Visa/Migration Consultation**?"
> (uk/cs/ru equivalents, matching the tone of the existing `_service_reprompt` templates)

### 3. New `lead_capture` steps

Two new `lead_step` values.

**`awaiting_consultation_type`** — entered when `_step_start` or `_step_awaiting_service` detects `consultation_ambiguous`. New handler `_step_awaiting_consultation_type`:
- Re-run `FormValidator.detect_service` on the reply; if it resolves to `legal_consultation` or `visa_consultation`, proceed exactly as `_step_awaiting_service` would for any other newly-detected service (i.e., fall into the `has_price_been_shown` check below).
- If it resolves to neither (still ambiguous, or unrelated), re-return the same `CONSULTATION_TYPE_PROMPT` (reprompt, step unchanged).
- If it's a question (`FormValidator.is_user_asking_question`), hand off to `chat` — same pattern as `_check_question_trap`, which must add `"awaiting_consultation_type"` to its handled-steps tuple (currently `("awaiting_name", "awaiting_phone", "awaiting_email")`).

**`awaiting_contact_confirmation`** — entered once a concrete service (not the ambiguous sentinel) is known *and* `FormValidator.has_price_been_shown(state.conversation_history)` is `True`. New handler `_step_awaiting_contact_confirmation`:
- Reuses the same affirmative/negative word-matching approach already established in `gate.py`'s `is_affirmative_reply_to_manager_prompt` (`_AFFIRMATIVE_WORDS = {"ano", "yes", "так", "да", "chci", "y"}`) — extract this set (or an equivalent) into a shared location both modules can use, plus a matching negative-word set (`{"ні", "нет", "no", "ne"}` — same as `lead_capture.py`'s existing `_SKIP_EMAIL_WORDS`, reuse that constant).
- Affirmative → `lead_step="awaiting_name"`, response = existing `_service_reprompt`-style "How should I address you?" prompt (reuse `MESSAGES[lang]["start"]` wording, unchanged), and explicitly set `"route": Route.LEAD` in the returned dict — matching `_step_awaiting_name`/`_step_awaiting_phone`'s existing pattern for a successful step advance (functionally redundant with the wrapper's own default for this outcome, but keeps the handler's return value consistent and directly unit-testable like its siblings).
- Negative → apply `_RESET_FIELDS` (sets `lead_step=None`), response = new `CONTACT_DECLINED_MESSAGE` dict (new, 4 languages): "No problem — let us know if you have any other questions!" (matching the tone you confirmed). **Implementation note on routing:** `_step_awaiting_contact_confirmation` is a step handler, not an intercept — `lead_capture_node`'s wrapper (`nodes/lead_capture.py:270-274`) *always* overwrites whatever `"route"` a step handler returns, based on `route_to_llm`/`lead_step == "completed"`, defaulting to `Route.LEAD` otherwise. The handler must NOT try to set `"route"` itself (it would be silently discarded); returning `route_to_llm` unset/falsy and `lead_step=None` (not `"completed"`) is sufficient — the wrapper's default `Route.LEAD`, combined with `graph.py`'s `Route.LEAD.value: END` edge, ends the turn correctly. This is the exact same mechanism the affirmative branch above relies on too (`lead_step="awaiting_name"` + default `Route.LEAD` → `END` for *this* turn; the *next* real message resumes at `awaiting_name` via `gate`'s mid-form check) — not a special case.
- A question → hand off to `chat` (extend `_check_question_trap`'s step tuple to include `"awaiting_contact_confirmation"` too).
- Anything else unclear → reprompt the same yes/no question unchanged.

**`_step_start` change** — full new branching, consolidating the ambiguous-service case from §2 with the concrete-service case below (today it only has the "no service at all" vs. "service detected → straight to `awaiting_name`" branches):
1. No service detected at all → unchanged, `SERVICES_LIST_RESPONSE`, `lead_step="awaiting_service"`.
2. `detect_service` returns `"consultation_ambiguous"` → `CONSULTATION_TYPE_PROMPT`, `lead_step="awaiting_consultation_type"` (§2).
3. A concrete service is detected (including `legal_consultation`/`visa_consultation` directly, if the first message was already specific) — apply the same `has_price_been_shown` check `_step_awaiting_service` already does:
- Price not yet shown → `route_to_llm=True`, `current_service` set (hands off to `chat`, which explains pricing from `company_info.md`).
- Price already shown (rare on a true first message, but possible if `conversation_history` already contains it from an earlier session) → `lead_step="awaiting_contact_confirmation"`.

**`_step_awaiting_service` change:** currently, once `has_price_been_shown` is `True`, it goes straight to `lead_step="awaiting_name"`. Change the target to `lead_step="awaiting_contact_confirmation"` instead, for consistency with the new gate.

**`_STEP_HANDLERS` dict** gains the two new entries: `"awaiting_consultation_type": _step_awaiting_consultation_type`, `"awaiting_contact_confirmation": _step_awaiting_contact_confirmation`.

### 4. Universal call-timing fast-path

`nodes/chat.py::chat_node`, immediately after computing `lang = state.language or "uk"` and before building the tool/LLM call: check `FormValidator.is_asking_call_timing(state.incoming.text)`. If true, return the deterministic response without calling the LLM — no tool binding, no `company_info.md` read needed for this turn (still fine to read the file for consistency/simplicity, but the LLM call itself is skipped).

**Weekend wiring** (both this new chat-level fast-path *and* the existing `lead_capture.py::_check_call_timing` intercept): before returning `WHEN_WILL_YOU_CALL_RESPONSE[lang]`, check `FormValidator.has_weekend_mention(state.incoming.text)`. If true, prepend `WEEKEND_NOTICES[lang]` to the response (the two dicts are already written to concatenate naturally — `WEEKEND_NOTICES` entries end with `\n\n` and don't repeat the "contact you" sentence).

**`WHEN_WILL_YOU_CALL_RESPONSE["uk"]`** wording tightened to match the client's exact requested phrasing: `"строки"` → `"сроки"`, add `"з"` before `"понеділка"`, add `"годинами"` at the end. (The other 3 languages are already worded consistently with this and don't need changes — the client only gave the Ukrainian wording verbatim.)

### 5. Testing

New/updated test files, following the existing pattern (`test_gate.py`, `test_lead_capture.py`, `test_language_detection.py` — direct unit tests against the pure/deterministic functions, mocking the LLM-dependent `FormValidator` calls where unavoidable, exactly as `test_lead_capture.py` already does via `_mock_hostility_llm()`):

- `SERVICE_PATTERNS` split: `detect_service` returns `legal_consultation`/`visa_consultation`/`consultation_ambiguous` correctly for representative phrases in all 4 languages, and that other existing service IDs are unaffected.
- `_step_awaiting_consultation_type`: resolves on a clear reply, reprompts on an unclear one, hands off to chat on a question.
- `_step_awaiting_contact_confirmation`: affirmative → `lead_step == "awaiting_name"`; negative → `lead_step is None` and the fields in `_RESET_FIELDS` are cleared (per the routing note in §3, do **not** assert a `"route"` value on the raw handler's return for the negative case — these unit tests call the step function directly, bypassing `lead_capture_node`'s wrapper, so route-computation for this outcome is the wrapper's job, already covered separately by `test_routing.py`); question → `route_to_llm` truthy (wrapper turns this into `Route.CHAT`); unclear → reprompt (step unchanged).
- `_step_start`/`_step_awaiting_service`: price-not-shown → hands to chat; price-shown → lands on `awaiting_contact_confirmation`, not `awaiting_name`.
- `chat_node`'s new call-timing fast-path: `get_llm` not called when the question matches; weekend-mention prepends `WEEKEND_NOTICES`; non-call-timing messages proceed to the LLM as before (regression guard).
- Full `poetry run pytest -v` run clean before every commit, matching this session's established practice.

**Explicitly not covered by tests** (same caveat noted in the design conversation): `chat`'s own free-text pricing explanation when handed off pre-confirmation remains LLM-generated prose — its content quality is a prompt-engineering concern, not something this design changes or can unit-test.

## Open items for the implementation plan

- Exact new `agent_rules/strings.py` dict contents (`CONSULTATION_TYPE_PROMPT`, `CONTACT_CONFIRMATION_PROMPT`, `CONTACT_DECLINED_MESSAGE`, updated `SERVICE_LOCALIZED_NAMES`) in all 4 languages — draft during plan-writing, following the tone of the existing `PHONE_REPROMPT`/`EMAIL_REPROMPT`/`_CANCEL_MESSAGES` entries.
- Whether to extract the affirmative/negative word-matching helper into a shared module (`agent_rules/` seems the natural home, e.g. `agent_rules/affirmation.py`) now that both `gate.py` and `lead_capture.py` need it, versus duplicating the small constant — lean toward extracting, decide during planning.
