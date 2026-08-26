# SUMMARY.md

Changelog of fixes and infrastructure changes made to this repo, with commit hash and timestamp. Newest first.

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
