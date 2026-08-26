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

- **`gate`** (`nodes/gate.py`, `classify_lead_intent`) — the entry node. A binary classifier, not a 5-way
  one: it decides only `wants_lead` (clear commitment to proceed, or an explicit request for a human) via
  one LLM structured-output call, plus the same aggressive-message flagging the old supervisor had. Two
  cheap intercepts run first: if a lead-capture form is already active (`lead_step` set, not `"completed"`),
  the LLM call is skipped entirely (`routing.py::route_after_gate` sends the turn straight to `lead_capture`
  regardless of what `gate` returns); a deterministic heuristic also catches a bare "yes"/"так"/"ano" reply
  immediately after the bot itself asked "want us to contact you?", without a model call.
- **`lead_capture`** (`nodes/lead_capture.py`) — unchanged: a manually-coded multi-step form (service → name
  → phone → email) driven by `state.lead_step`, with regex+LLM field validation in `agent_rules/form_validator.py`.
  On completion it notifies staff via Telegram. It can hand off mid-form to `chat` (`Route.CHAT`) when the
  user asks a question instead of answering, or end the turn (`Route.END`) after a reprompt or a completed
  step — see `routing.py::route_after_lead_capture`'s docstring for why `Route.LEAD` must map to `END` here
  and not back into `lead_capture` itself (a same-turn self-loop that used to hit `GraphRecursionError`,
  fixed 2026-08-26).
- **`chat`** (`nodes/chat.py`, `chat_node`) — everything else: FAQ answering, identity questions, off-topic
  redirects, and handoff-for-unanswerable-questions, all in one LLM node. It reads `src/assets/company_info.md`
  fresh from disk on every call and injects the whole file into the system prompt — this is the single source
  of truth for services, pricing, required documents, contact/office/hours, and FAQ, in all four languages;
  edit that file and the very next message reflects the change, no reload or restart. Bound to one tool,
  `log_unanswered_question` (`tools/chat_tools.py`, wraps `core_api.store_unanswered_question` against the
  *real* `conversation_id` — the old `escalation.py` this replaced stubbed a throwaway `uuid4()` here and
  silently orphaned every logged question). Calling it short-circuits straight to a canned
  `HANDOFF_MESSAGES[lang]` reply (`prompts/handoff.py`) instead of letting the model free-generate what gets
  promised to a client.

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

`src/bots/utils/notify_stuff.py` sends manager-facing Telegram alerts (new lead, media received, aggressive
message, contacts shown) directly via the aiogram `bot` instance, imported lazily inside each function to avoid
a circular import with `src/bots/tgbot/bot.py`. None of the four functions guard their own `bot.send_message`
call with a try/except — whether a failure is swallowed depends entirely on the call site. The aggressive-
message alert is guarded (`nodes/gate.py` wraps it in `try/except Exception: pass`). The lead-capture
completion alert (`nodes/lead_capture.py`, `notify_manager_lead_telegram`) is **not** guarded and runs before
the "thank you" response is built — if that Telegram send fails, the client who just finished the form gets
no confirmation message at all, not even a generic error.
