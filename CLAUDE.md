# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ulp_bot` is the AI chat-bot worker for a single client ("United Legal Partners", a Prague law firm — see
`src/ai/conversation_agent/services/email_sender.py` for the hardcoded firm details). It runs as one long-lived
process per deployment (`CLIENT_ID` env var identifies the tenant), currently polling Telegram, and delegates
all persistence (conversations, chat history, unanswered questions) to an external "Core API" backend service
that is **not** part of this repo — see `src/api_client/core_api.py`. There is no local database and no vector store — company info lives in a single Markdown file
(see "Company info" below).

## Commands

This project uses Poetry (Python `>=3.12,<3.15`).

```bash
poetry install          # install dependencies
poetry run python src/main.py   # run the Telegram bot worker locally (requires a filled .env)
```

Docker:
```bash
docker compose up -d --build --force-recreate ulp_bot
```
Deploys are automatic: pushing to `main` triggers `.github/workflows/deploy.yml`, which SSHes into the VPS,
`git pull`s, and re-runs the compose command above. There is no CI test/lint gate before deploy.

### Configuration

All runtime config is a single `pydantic-settings` model in `src/config.py`, loaded from `.env` (see that file
for the full list of required variables — most have no default and the process will fail to start without them).
Key groups: Telegram token, Core API URL, LLM provider/model + OpenAI key, company info file path
(`company_info_path`), Google Calendar booking config, and SMTP for booking confirmation emails.

### Tests

```bash
poetry run pytest -v              # full suite
poetry run pytest tests/test_gate.py -v   # single file
```

`tests/conftest.py` stubs every required `Settings` field via `os.environ.setdefault(...)` so test modules
can import `src.*` without a real `.env` — see its docstring before adding a new required (no-default)
field to `src/config.py`, or tests will start failing on collection.

### Company info

`src/assets/company_info.md` is the single source of truth for everything the `chat` node tells users about
the firm — services, pricing, required documents, contact/office/hours, FAQ — in all four supported
languages (en/uk/cs/ru). It's read fresh from disk on every `chat` turn (`nodes/chat.py::_read_company_info`),
so editing it takes effect on the very next message with no reload, restart, or deploy step. There is no
vector search or embeddings involved — the whole file is injected into the system prompt directly.

## Architecture

### Message flow

`src/bots/tgbot/bot.py` starts an aiogram `Dispatcher` polling Telegram. Text messages go through
`src/bots/tgbot/handlers/message.py` → `src/bots/shared/handler.py::handle_incoming`, which is the **single
entry point all bots funnel through** (so a future WhatsApp/Instagram bot — stub dirs already exist under
`src/bots/whatsbot`, `src/bots/instabot` — would reuse it):

1. Fetch/create a conversation and recent history from the Core API (`core_api.py`).
2. Invoke the LangGraph `graph` (`src/ai/conversation_agent/graph.py`), keyed by `thread_id=client_id` so
   LangGraph's own `MemorySaver` checkpointer keeps per-user graph state (e.g. `lead_step`) across turns —
   this is a separate, in-process memory layer from the Core API's persisted chat history.
3. Persist the bot's reply back to the Core API and return the text to send.

### The conversation graph

`src/ai/conversation_agent/` implements a LangGraph state machine (`AgentState` in `state.py`) with three
nodes:

- **`gate`** (`nodes/gate.py`, `classify_lead_intent`) — the entry node. Not a 5-way classifier: it decides
  `wants_lead` (clear commitment to proceed, or an explicit request for a human) via one LLM structured-output
  call, plus two narrower flags on the same call — `explicit_human_request` (true only for the "wants a
  human/is frustrated about being reached" subset of `wants_lead`, not an ordinary service booking) and
  `is_aggressive` (hostile/profane messages). Both are classified and logged for visibility only, per user
  policy: the manager is only ever notified on Telegram for a completed lead with contact details, not for
  hostility alone (2026-08-26) and not for `explicit_human_request` on its own either, for now (2026-08-27 —
  briefly wired up to notify immediately, same day rolled back: it was firing on messages like "call me on
  Saturday", a call-timing question rather than a genuine escalation, and promising a callback the bot had no
  contact details to make good on). See "Staff notifications" below. Two cheap intercepts run first: if a
  lead-capture form is already active (`lead_step` set, not `"completed"`), the LLM call is skipped entirely
  (`routing.py::route_after_gate` sends the turn straight to `lead_capture` regardless of what `gate` returns);
  a deterministic heuristic also catches a bare "yes"/"так"/"ano" reply immediately after the bot itself asked
  "want us to contact you?", without a model call. `wants_lead` must be TRUE for a bare need-statement that
  names one of the firm's actual services (e.g. "Потрібна консультація" - "need a consultation") even without
  an explicit "book" verb - that's what hands off to `lead_capture`'s `awaiting_consultation_type`
  disambiguation below. Client-reported 2026-08-28: the prompt's own FALSE example, "Потрібен юрист" ("need A
  LAWYER" - vague, names no specific service), was being over-generalized by the model onto this
  service-naming case too, so the message fell through to `chat` instead and got an inconsistent free-generated
  reply (sometimes the full price list, sometimes just "call the manager", depending on conversation history -
  see `chat`'s "don't repeat yourself" rule below) rather than the deterministic disambiguation question.
  `prompts/gate.py` now spells out the distinction explicitly.
- **`lead_capture`** (`nodes/lead_capture.py`) — unchanged in spirit, but the pre-name-collection
  sequence was redesigned 2026-08-27 after real client feedback: a detected service now goes through
  `awaiting_consultation_type` (only for an ambiguous bare "consultation" — disambiguates legal vs.
  visa/migration) and `awaiting_contact_confirmation` (a universal yes/no gate, entered once pricing
  has been shown via `FormValidator.has_price_been_shown`) before ever reaching `awaiting_name`. A "no"
  at the confirmation gate resets the form without collecting any personal data. On completion it
  notifies staff via Telegram. It can hand off mid-form to `chat` (`Route.CHAT`) when the user asks a
  question instead of answering, or end the turn (`Route.END`) after a reprompt or a completed step —
  see `routing.py::route_after_lead_capture`'s docstring for why `Route.LEAD` must map to `END` here
  and not back into `lead_capture` itself (a same-turn self-loop that used to hit `GraphRecursionError`,
  fixed 2026-08-26). Its `_check_cancel` intercept (`FormValidator.is_user_cancelling`) resets the whole
  in-progress form (`_RESET_FIELDS` — name/phone/email/service all dropped), so as of 2026-08-28 it is
  judged purely by `CANCEL_KEYWORDS`, no LLM call involved — it used to also short-circuit true on
  `is_profanity_or_hostile`, which destroyed an active booking on a client-reported false positive: the
  surname "Катерина Мат" (a truncated "Матвієнко"/"Матюк"-type name) contains "мат", itself the RU/UK
  noun for "swearing", and the hostility classifier flagged the word rather than any actual abuse in the
  message. `is_valid_name`/`extract_phone`/`extract_email` still gate on `is_profanity_or_hostile` -
  a false positive there only costs a harmless reprompt, not the whole form, so they were left as-is.
- **`chat`** (`nodes/chat.py`, `chat_node`) — everything else: FAQ answering, identity questions, off-topic
  redirects, and handoff-for-unanswerable-questions, all in one LLM node. Also fast-paths call-timing questions
  ("when will you call me?", weekend-mention special case) before any LLM call — this used to only be
  guaranteed inside an active lead form; reinstated everywhere 2026-08-27, same day changed again to redirect
  to the firm's own contact channels (`HANDOFF_MESSAGES`) rather than promise a callback: this intercept can
  fire before any contact details are ever collected, so "we'll call you" was a promise the bot had no phone
  number to keep. `lead_capture.py`'s `_check_call_timing` mirrors this exactly, same `HANDOFF_MESSAGES` reuse.
  It reads
  `src/assets/company_info.md` fresh from disk on every call and injects the whole file into the system
  prompt — this is the single source of truth for services, pricing, required documents, contact/office/hours,
  and FAQ, in all four languages; edit that file and the very next message reflects the change, no reload or
  restart. Bound to one tool, `log_unanswered_question` (`tools/chat_tools.py`, wraps
  `core_api.store_unanswered_question` against the *real* `conversation_id` — the old `escalation.py` this
  replaced stubbed a throwaway `uuid4()` here and silently orphaned every logged question). Calling it
  short-circuits straight to a canned `HANDOFF_MESSAGES[lang]` reply (`prompts/handoff.py`) instead of
  letting the model free-generate what gets promised to a client.

Graph wiring (`graph.py` + `routing.py`): `gate` is the entry point and conditionally routes to `lead_capture`
or `chat`. `lead_capture` can hand back to `chat` or end the turn. `chat` always ends the turn.

There used to be a pgvector-backed knowledge base here (`ai/knowledge/store.py`, `embeddings.py`,
`faq_loader.py`, `src/assets/faq.yaml`) — it's gone. It was already non-functional in practice
(`load_faq()` was never called from anywhere in the codebase, so the KB was very likely always empty in
production) and, per the single-file design above, isn't needed. `ai/knowledge/llm.py` (a generic
`ChatOpenAI` factory, unrelated to that pipeline despite the old path) moved to `ai/llm.py`.

### Localization

The bot is multilingual (uk/cs/ru/en). Language is detected per-message via `langdetect` in
`src/bots/utils/language_detection.py` (with a short-word fast path and a `SUPPORTED_LANGUAGES` allowlist that
falls back to the conversation's existing language). Nearly every user-facing string is a `dict[lang, str]`
constant, centralized in `src/ai/conversation_agent/agent_rules/strings.py` — when adding a new user-facing
message, add it to all four languages there rather than inlining a new string in a node.

### Staff notifications

`src/bots/utils/notify_stuff.py` sends manager-facing Telegram alerts directly via the aiogram `bot` instance,
imported lazily inside each function to avoid a circular import with `src/bots/tgbot/bot.py`. Two functions
are actually wired up: `notify_manager_lead_telegram` (called from `nodes/lead_capture.py`'s completion step,
once the full name/phone/email form is done — **not** try/except-guarded and runs before the "thank you"
response is built, so a failed Telegram send leaves the client with no confirmation message at all) and
`notify_manager_media_telegram` (called from `bots/tgbot/handlers/message.py` on any non-text message).

Two more functions exist in this file but are currently uncalled from anywhere, both rolled back the same day
they were tried, for the same reason — a signal that seemed like "wants a human" fired on messages that
weren't genuine escalations:
- `notify_manager_aggressive_telegram` — per user policy (2026-08-26), hostile messages are still logged
  (`gate.py`'s `is_aggressive`) but no longer ping the manager on their own.
- `notify_manager_human_request_telegram` — briefly wired into `nodes/gate.py`'s `classify_lead_intent` on
  2026-08-27 (both the LLM classification path and the deterministic "yes"-after-manager-prompt shortcut), to
  notify staff immediately on `explicit_human_request`, before the form completes. Rolled back the same day:
  it fired on messages like "call me on Saturday" (a call-timing question, not an escalation) and implied a
  callback the bot had no contact details to make good on. `explicit_human_request` is still classified and
  logged for visibility. If this comes back, `gate.py`'s `_notify_human_request` helper (also removed, see git
  history) wrapped the call in try/except deliberately — unlike the unguarded `notify_manager_lead_telegram`
  call above, a failed Telegram send here must never break the conversation turn for the client.

`notify_manager_contacts_telegram` has never had a caller (pre-existing, unrelated to either rollback above).
