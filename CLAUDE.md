# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`ulp_bot` is the AI chat-bot worker for a single client ("United Legal Partners", a Prague law firm — see
`src/ai/conversation_agent/services/email_sender.py` for the hardcoded firm details). It runs as one long-lived
process per deployment (`CLIENT_ID` env var identifies the tenant), currently polling Telegram, and delegates
all persistence (conversations, chat history, unanswered questions) to an external "Core API" backend service
that is **not** part of this repo — see `src/api_client/core_api.py`. There is no local database; PostgreSQL
(`db_url`/`db_schema` settings) is used only as a pgvector knowledge-base store for RAG.

## Commands

This project uses Poetry (Python `>=3.12,<3.15`).

```bash
poetry install          # install dependencies
poetry run python src/main.py   # run the Telegram bot worker locally (requires a filled .env)
```

There is no lint/format/test tooling configured (no ruff/black/pytest config, no test suite in the repo).
Don't assume any of these commands exist — verify before suggesting them to the user.

Docker:
```bash
docker compose up -d --build --force-recreate ulp_bot
```
Deploys are automatic: pushing to `main` triggers `.github/workflows/deploy.yml`, which SSHes into the VPS,
`git pull`s, and re-runs the compose command above. There is no CI test/lint gate before deploy.

### Configuration

All runtime config is a single `pydantic-settings` model in `src/config.py`, loaded from `.env` (see that file
for the full list of required variables — most have no default and the process will fail to start without them).
Key groups: Telegram token, Core API URL, LLM provider/model + OpenAI key, embeddings model, FAQ path, RAG
tuning (`context_window`, `retrieval_k`, `similarity_threshold`), Google Calendar booking config, and SMTP for
booking confirmation emails.

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

`src/ai/conversation_agent/` implements a LangGraph state machine (`AgentState` in `state.py`) with nodes in
`nodes/`:

- **`supervisor.py`** (`classify_intent`) — the entry node. Runs a few cheap intercepts first (a "when will you
  call me" pattern match, an affirmative-reply-to-a-manager-prompt heuristic) before falling back to an LLM
  structured-output call that classifies intent and flags aggressive/hostile messages (which fires a
  fire-and-forget staff Telegram alert). Maps intent → `Route` enum (`routes.py`).
- **`lead_capture.py`** — a manually-coded multi-step form (service → name → phone → email) driven by
  `state.lead_step`, not an LLM conversation. Each step has interceptors (cancel, "user is asking a question
  instead of answering", call-timing) checked before the step handler. On completion it notifies staff via
  Telegram (`notify_manager_lead_telegram`). Field validation (name/phone/email/service detection, profanity
  checks) lives in `agent_rules/form_validator.py`, which itself calls the LLM for fuzzy checks like
  "is this a real name" — validation is not purely regex-based.
- **`info.py`** — general Q&A: retrieves from the pgvector knowledge store (`ai/knowledge/store.py`) and answers
  via LLM with retrieved context injected into the system prompt.
- **`escalation.py`**, **`off_topic.py`**, **`call_timing.py`** — smaller terminal nodes for handoff-to-human,
  off-topic messages, and "when will you call" replies.

Graph wiring (`graph.py`): `supervisor` is the entry point and conditionally routes to `info` / `lead_capture` /
`escalation` / `off_topic` / `call_timing`. Notably, `_route_after_supervisor` overrides the classifier's route
whenever a lead-capture form is mid-flight (`lead_step` set and not `"completed"`), so an in-progress form
always wins over re-classification. `lead_capture` has its own conditional exit edges (it can hand off to
`info` or `escalation` mid-form, loop back to itself, or reach `END`). All other nodes go straight to `END`.

### Knowledge base

`src/ai/knowledge/`: `store.py` wraps `langchain_postgres.PGVector` (async, `postgresql+psycopg://`) scoped to
a `{schema}_knowledge_base` collection; `faq_loader.py` is an offline/setup script that loads a multilingual
YAML FAQ file into it; `llm.py`/`embeddings.py` are thin factories around `ChatOpenAI`/`OpenAIEmbeddings`
(Anthropic/Gemini/HuggingFace alternatives are commented out but not wired up — swapping providers means
editing these factories, not just config).

### Localization

The bot is multilingual (uk/cs/ru/en). Language is detected per-message via `langdetect` in
`src/bots/utils/language_detection.py` (with a short-word fast path and a `SUPPORTED_LANGUAGES` allowlist that
falls back to the conversation's existing language). Nearly every user-facing string is a `dict[lang, str]`
constant, centralized in `src/ai/conversation_agent/agent_rules/strings.py` — when adding a new user-facing
message, add it to all four languages there rather than inlining a new string in a node.

`src/ai/conversation_agent/data/strings.py` and `src/ai/conversation_agent/data/lang.py` also exist but are
**dead code** — leftovers from an incomplete migration (nothing in the codebase imports `data.lang`, and the
only importer of `data.strings` is `data.lang` itself). Don't add strings there; nothing reads them.

### Staff notifications

`src/bots/utils/notify_stuff.py` sends manager-facing Telegram alerts (new lead, media received, aggressive
message, contacts shown) directly via the aiogram `bot` instance, imported lazily inside each function to avoid
a circular import with `src/bots/tgbot/bot.py`. None of the four functions guard their own `bot.send_message`
call with a try/except — whether a failure is swallowed depends entirely on the call site. Only the aggressive-
message alert is actually guarded (`supervisor.py` wraps it in `try/except Exception: pass`). The lead-capture
completion alert (`lead_capture.py`, `notify_manager_lead_telegram`) is **not** guarded and runs before the
"thank you" response is built — if that Telegram send fails, the client who just finished the form gets no
confirmation message at all, not even a generic error.
