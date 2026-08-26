# SUMMARY.md

Changelog of fixes and infrastructure changes made to this repo, with commit hash and timestamp. Newest first.

---

## 2026-08-26 16:58:43 +0200 — `158c166`
**Fix "I need a lawyer"-style English sentences misdetected as unsupported languages**

The previous greeting-word fix (see the `eba8fec` entry below) only patched exact short words. A
full English sentence hit the same underlying problem: `langdetect`'s single top-1 guess for "I
need a lawyer" is `cy` (Welsh) at 71% confidence, with `en` a real but discarded second-place
candidate at 29% — confirmed live in production (`gate_classified language=uk` for an English
message, then the bot replied in Ukrainian). Found by the user testing right after the previous
greeting fix shipped.

Root-cause fix, not another word-list patch: `detect_lang` now uses `detect_langs()` (ranked
candidates, not just the single best guess) and returns the highest-ranked candidate that's
actually in `SUPPORTED_LANGUAGES`, instead of trusting the top-1 guess even when it's a language
we don't support at all. Only changes behavior when the top guess isn't supported to begin with —
verified against real `langdetect` output that this doesn't regress any previously-correct case,
and that genuinely unsupported languages (German, French) still fall through to the default
correctly. Regression tests added.

---

## 2026-08-26 16:47:40 +0200 — `6a68982`
**Log the actual reply text and classification reasoning**

Requested during production testing: `docker compose logs` showed event names (`gate_classified`,
`chat_replied`) but not the reply content or why a decision was made, making it hard to verify
behavior from logs alone.

- `handler.py`: single `response_sent` log at the one choke point all replies pass through, with
  the full response text, detected intent, and detected language — covers `chat`, `lead_capture`,
  and the empty-response fallback in one place.
- `gate.py`: `gate_classified` now also logs `is_aggressive` and `language` (previously only
  `wants_lead`); the mid-form skip branch now logs its own decision too (previously silent unless
  profanity was flagged).

---

## 2026-08-26 16:41:57 +0200 — `eba8fec`
**Fix common greetings in en/cs/ru misdetected as unrelated languages**

`langdetect` is unreliable on short text generally, but greetings are a specific, verified
production bug: `detect("hello") == "fi"`, `detect("hi") == "sw"`, `detect("hey") == "so"`,
`detect("ahoj") == "so"`, `detect("привет") == "mk"` — none of these detect as their actual
language, so a plain "hello" fell through to the hardcoded `"uk"` default and the bot replied in
Ukrainian to an English greeting. Live in production; found via manual testing right after deploy.

Fix: extended the existing `_SHORT_WORDS_MAP` fast path (already used for так/ні/yes/no/ano/ne/
да/нет) to cover common greetings in all 4 supported languages, verified against real `langdetect`
output for each. Also strips trailing punctuation before the fast-path lookup so "Hello!" hits it
too, not just the bare word. Regression test added (`tests/test_language_detection.py`).

---

## 2026-08-26 16:31:32 +0200 — `f5dc018`
**Log timestamps in Prague time, allowlist checkpoint types, commit poetry.lock**

- `logger.py`: `structlog`'s `TimeStamper` defaulted to UTC (2h behind Prague in summer), read as
  wrong in production logs. Custom processor now uses the same `ZoneInfo("Europe/Prague")` pattern
  already used for booking emails.
- `graph.py`: `MemorySaver`'s default `JsonPlusSerializer` warned on every checkpoint
  serialize/deserialize of `IncomingMessage`/`Route` ("unregistered type... will be blocked in a
  future version"). Explicitly allowlisted both.
- `poetry.lock` is no longer gitignored and is now committed: every deploy was re-resolving
  dependency versions from scratch with no pin, which is how `langgraph` silently moved to a
  version that introduced the msgpack warning above with zero code change on our end.

---

## 2026-08-26 14:29:08 +0200 — `219e10d` (14 commits, `bb8fdb1..219e10d`)
**Replace the 6-node supervisor/info/lead_capture/escalation/off_topic/call_timing graph with gate/chat/lead_capture**

Full plan: `docs/superpowers/plans/2026-08-26-conversational-graph-refactor.md`.

- `gate` (binary lead-intent classifier) replaces the old 5-way `supervisor` classifier.
- `chat` (one LLM node, bound to a single `log_unanswered_question` tool) replaces
  `info`/`off_topic`/`escalation`/`call_timing`. Grounded entirely in a new single source of
  truth, `src/assets/company_info.md` (services, pricing, required documents, contact/office/
  hours, FAQ, in en/uk/cs/ru), read fresh from disk on every turn — no reload/restart needed to
  edit it.
- `lead_capture`'s state machine is unchanged, apart from 3 `Route.INFO` → `Route.CHAT` renames.
- Fixed a real production bug along the way: `lead_capture`'s exit-edge map routed `Route.LEAD`
  back to `lead_capture` itself, causing a same-turn self-loop and `GraphRecursionError` whenever
  a step reprompted or advanced (e.g. every message like "Зателефонуйте мені" that didn't look
  like a valid name/phone/email — this was the original bug report that started this work). Now
  maps to `END`; the next real message resumes the form via `gate`'s own active-form check. Pinned
  with a regression test.
- Retired the pgvector knowledge-base pipeline (`KnowledgeStore`, `embeddings.py`,
  `faq_loader.py`, `assets/faq.yaml`, the `langchain-postgres` dependency) — it was already
  non-functional (`load_faq()` was never called from anywhere in the codebase, so the KB was very
  likely always empty in production).
- Added a test suite from scratch (pytest + pytest-asyncio; this repo had none before).

Built via subagent-driven development in an isolated worktree, with per-task review and a final
whole-branch review before merge.

---

## 2026-08-26 10:12:58 +0200 — `8fbe0f9`
**Fix info_agent returning wrong state keys, correct CLAUDE.md**

`info_agent` (`src/ai/conversation_agent/nodes/info.py`) returned
`{"messages": [...], "next_route": ...}`, but `AgentState`'s real fields are
`response`/`route` — every other node (`supervisor`, `lead_capture`,
`escalation`, `off_topic`) uses them. Since nothing set `response`,
`handler.py` fell through to the generic empty-response fallback
("Sorry, something went wrong on our end...") for every message routed to
`info` — greetings, general questions, and `unknown` intent, the most
common path through the bot. This was live in production.

Fix: builds LLM context from `conversation_history` like the other nodes
(instead of the unpopulated `state.messages`) and returns `response`/`route`
correctly.

Also corrected two inaccuracies in the just-generated `CLAUDE.md`:
- `data/strings.py` and `data/lang.py` are dead code (nothing imports
  `data.lang`; the only importer of `data.strings` is `data.lang` itself) —
  not a second live location for user-facing strings.
- Staff notifications are not uniformly best-effort. Only the
  aggressive-message alert is `try/except`-guarded (in `supervisor.py`).
  The lead-capture completion alert (`notify_manager_lead_telegram`) is not
  guarded and runs before the "thank you" response is built — a failed
  Telegram send there means the client gets no confirmation at all.

---

## 2026-08-26 09:49:56 +0200 — `7543919`
**Add VPS auto-deploy on push to main**

Added `.github/workflows/deploy.yml`: on every push to `main`, SSHes into
the VPS, `git pull origin main`, and runs
`docker compose up -d --build --force-recreate ulp_bot`. Mirrors the
existing deploy pattern used by `langgraph-python-prototype`, reusing the
same VPS deploy key (`VPS_SSH_KEY`). Repo secrets added: `VPS_HOST`,
`VPS_USER`, `VPS_SSH_KEY`, `VPS_DEPLOY_PATH`
(`/opt/autopilot_test/clients/ULP/ulp_bot`, the directory actually running
the live container — not `/opt/autopilot`, which tracks a different repo
and wasn't running).

---

## 2026-08-26 09:48:24 +0200 — `d9b5989`
**Fix broken import in lead_capture.py after revert**

`main`'s prior commit (a revert of "global fix of strings.py and
lead_capture.py. Added form_validator.py") rolled `strings.py`,
`form_validator.py`, and the language-detection module layout back to an
older shape, but `lead_capture.py` itself was left pointing at the newer
(now-reverted) module paths. Missing on import: `WEEKEND_NOTICES` (existed
under a different module), `EMAIL_REPROMPT` (didn't exist anywhere),
`data.form_validator.FormValidator` (module didn't exist), and
`data.lang.get_lang` (function didn't exist). The container crash-looped
on every startup as a result — the live Telegram bot was completely down.

Fix: restored `lead_capture.py` to match `bacf6f7` ("global fix again9"),
the last commit confirmed to run cleanly (verified: none of the modules it
depends on — `agent_rules/strings.py`, `agent_rules/form_validator.py`,
`routes.py`, `src/bots/utils/language_detection.py` — differ between
`bacf6f7` and the broken revert commit).

Deployed manually to the VPS ahead of this commit (rolled the running
container back to `bacf6f7` first to restore service immediately), then
this commit brought `main` itself back to a consistent, deployable state.
