# SUMMARY.md

Changelog of fixes and infrastructure changes made to this repo, with commit hash and timestamp. Newest first.

---

## 2026-08-28 14:30:02 +0200 — `8bef538`
**Cancellation no longer triggered by profanity/hostility detection alone**

Found via live client testing: mid-name-collection, "Катерина Мат" (a truncated
"Матвієнко"/"Матюк"-type surname) got the whole in-progress lead form wiped -
`_check_cancel` fired the generic "скасував запис" message even though the text
matches no `CANCEL_KEYWORDS`. Root cause: `is_user_cancelling` also
short-circuited `True` on `is_profanity_or_hostile`, an LLM call asked "does this
text contain profanity" - "мат" is itself the RU/UK noun for "swearing", so the
classifier plausibly flagged the word rather than any actual hostility in the
message. Not empirically confirmed against the real model (no API key in the
diagnosing environment) - established by elimination against the other two
candidate paths (`CANCEL_KEYWORDS`, the question-trap intercept), neither of
which matches this text.

Beyond this one false positive, gating a destructive action (`_RESET_FIELDS`
drops name/phone/email/service) on a generic hostility classifier was
inconsistent with the rest of this codebase's policy: `gate.py`'s
`is_aggressive` is logged but never acts alone.

Fix: `is_user_cancelling` now checks `CANCEL_KEYWORDS` only, no LLM call.
Genuine profane cancellations ("та ну нахуй, скасуй все") are still caught since
`CANCEL_KEYWORDS` matches regardless of tone; only the "flagged hostile but
never asked to cancel" case stops wiping the form.
`is_valid_name`/`extract_phone`/`extract_email` keep their
`is_profanity_or_hostile` gate - a false positive there only costs a harmless
reprompt, not the whole form. `tests/test_cancel_detection.py` added (3 new
tests, including one asserting `get_llm` is never called from
`is_user_cancelling` now). `CLAUDE.md` updated.

122 tests pass (was 119, +3). Not yet verified live - pushed for the VPS
auto-deploy, verification pending.

---

## 2026-08-28 14:20:06 +0200 — `5fcb286`
**Gate now treats a bare need for a named service (e.g. consultation) as wants_lead**

Found via live client testing: "Потрібна консультація" ("need a consultation") got
`wants_lead=False` from `gate.py` and fell through to `chat`'s free-form reply
instead of `lead_capture`'s deterministic `awaiting_consultation_type`
disambiguation - the exact "bot never asks which type" flow that step was built for
(`0e5ecec`). Symptom was also inconsistent across identical inputs: `chat` is
LLM-generated, not templated, and has a "don't repeat yourself" rule, so the same
message got the full price list the first time and just "call the manager" the
second time in the same conversation thread.

Root cause: `prompts/gate.py`'s own FALSE example, "Потрібен юрист" ("need A
LAWYER" - vague, names no specific service), was being over-generalized by the model
onto "Потрібна консультація" too, even though the latter names one of the firm's
actual bookable services.

Fix: `prompts/gate.py` now spells out the distinction explicitly - a need-statement
naming a specific service (consultation, POA, apostille, etc.) is `wants_lead=TRUE`
even without an explicit "book" verb; a vague need ("a lawyer", generically) stays
FALSE. `tests/test_gate.py` gets a regression test pinning the routing plumbing for
this case (mocked LLM output, per existing test style - doesn't verify the real
model's prompt-following). `CLAUDE.md` updated with the same distinction.

119 tests pass (was 118, +1). Not yet verified live - client can only test on the
VPS; pushed to `main` for the auto-deploy, verification pending.

---

## 2026-08-27 14:50:13 +0200 — `03dfcd7`
**Call-timing responses no longer promise a callback we can't make; rolled back the human-request manager notification**

Found via live testing: "Зателефонуйте мені в суботу" got a reply promising "our team
will contact you" - but this intercept fires before any contact details are ever
collected (`lead_step=None`, no phone captured), so that promise couldn't actually be
kept.

- `chat.py`'s call-timing fast-path and `lead_capture.py`'s `_check_call_timing` now
  return `HANDOFF_MESSAGES` (phone/email/office/hours - redirect the client to reach
  out themselves) instead of the removed `WHEN_WILL_YOU_CALL_RESPONSE` ("we will
  contact you" promise).
- `WEEKEND_NOTICES` (still prepended when a weekend day is mentioned) dropped its own
  "team will contact you" clause, keeping only the office-hours notice ahead of the
  `HANDOFF_MESSAGES` body.
- Per explicit user instruction, rolled back the `explicit_human_request` manager
  notification added earlier today: it was firing on exactly this kind of message (a
  call-timing question, not a genuine escalation) before there was ever anything urgent
  to page staff about. Removed `gate.py`'s `_notify_human_request` helper and both call
  sites, following the exact precedent already established for
  `is_aggressive`/`notify_manager_aggressive_telegram` - `explicit_human_request` is
  still classified and logged for visibility, `notify_manager_human_request_telegram`
  still exists in `notify_stuff.py` but nothing calls it, for now.
- `CLAUDE.md` updated for both changes.

118 tests pass (was 119; -4 notify-specific tests replaced with 2 regression guards
matching the `is_aggressive` pattern, +1 new test locking in the
redirect-to-contact-channels behavior).

---

## 2026-08-27 10:29:45 +0200 — `40e167b`
**Notify manager immediately on an explicit human request, before the form completes**

User-directed: the manager should be notified when a client explicitly wants a
human/manager to contact them, not only once the full name/phone/email form is
completed minutes later. This half of the existing 2026-08-26 notification policy was
never actually wired up - `notify_manager_lead_telegram` only ever fires from
`lead_capture.py`'s completion step, and pre-existing `is_human_handoff_requested` /
`HUMAN_HANDOFF_PATTERNS` machinery was dead code, never called from anywhere.

`gate.py`'s `LeadGateClassification` gets a new `explicit_human_request` field - a
narrower signal than `wants_lead` alone (true only for "wants a human / frustrated
about being reached", not an ordinary service booking), so staff aren't pinged before
there's anything urgent. Wired into both the LLM classification path and the
deterministic "yes"-after-manager-prompt shortcut, via a new
`notify_manager_human_request_telegram` (no contact details are known yet at this
point, so it just flags the conversation for staff to open themselves - complements
the existing full-detail notification, which still fires later if the form completes;
a client can trigger both by design). Deliberately try/except-wrapped so a failed
Telegram send never breaks the conversation turn for the client, unlike the existing
unguarded call in `lead_capture.py`. `CLAUDE.md`'s Staff notifications section
corrected - it previously described this as already working when it wasn't.

119 tests pass (115 + 5 new).

---

## 2026-08-27 10:19:23 +0200 — `36cb0fa`
**Chat replies were repetitive and didn't pivot to asking for contact info**

Found via live testing: after a user pushed back frustrated ("so where will you call if
you don't have my number?"), the bot just restated that it couldn't reach them and
repeated the phone number for the third time in four turns, instead of inviting them to
leave it right there in the chat.

Two coordinated prompt-text changes:
- `chat.py`'s `SYSTEM_PROMPT`: don't restate a fact (phone/address/hours) already given
  earlier in the same conversation unless asked again; pivot to inviting the user to
  share their name/phone in chat instead of repeating a dead end when they're frustrated
  or confused about how they'll be reached.
- `gate.py`'s `SYSTEM_PROMPT`: the pivot above would be a dead end on its own - the
  classifier's `wants_lead=TRUE` examples didn't cover a user simply volunteering a
  phone number/email/name (as opposed to an explicit "call me" or "yes"), so a reply to
  the new invite could stay stuck in `chat_node` with nothing to capture it. Added an
  explicit example: providing contact details IS the commitment, don't wait for a
  separate explicit yes first.

Pure prompt-text changes, no code paths affected - 115 tests pass unchanged, plus a
direct `.format()` sanity check on both prompts.

---

## 2026-08-27 10:09:25 +0200 — `67cc859`
**`detect_lang` misclassified unambiguous Ukrainian as Russian mid-conversation**

Found via live testing: "Як довго чекати?" (unambiguously Ukrainian to a human) got a
full Russian-language reply mid-conversation. Root cause: Ukrainian and Russian share
nearly the entire Cyrillic alphabet and huge amounts of vocabulary, so langdetect's
n-gram model is a coin-flip on short text containing neither language's diagnostic-only
letters (uk: `іїєґ`, ru: `ыэъё`) - verified directly, `detect_langs()` genuinely ranks
"ru" top for that exact sentence.

`detect_lang` now checks for those diagnostic letters first (a reliable, deterministic
signal when present). When they're absent and the statistical top guess lands on uk or
ru specifically, it now prefers the conversation's already-established language (the
`default` argument) over the coin-flip guess, instead of switching on it. A genuinely
Russian- or Ukrainian-diagnostic sentence still overrides an established default in the
other direction - this narrows the ambiguous-text behavior, it doesn't disable uk↔ru
switching. Verified with new regression tests in both directions.

115 tests pass (110 + 5 new).

---

## 2026-08-27 08:33:04 +0200 — `1cd05ad`
**Three production bugs from live Czech/Ukrainian testing of the redesigned lead-capture flow**

Found by testing the just-deployed lead-capture redesign directly against the bot:

- **Czech name capture looped forever.** `is_valid_name` hard-rejected any answer over 4
  words *before validation even ran*, so a natural sentence like "Moje jméno je Alex
  Test" never reached the LLM check at all - phone/email capture already tolerate full
  sentences via regex-search, name capture didn't. Added `strip_name_preamble()`
  (en/uk/ru/cs) and applied it both before validation and before storing `client_name`.
  Separately, the LLM name-validity prompt was too strict and inconsistent - it rejected
  "Alex test" / "Alex Vrn" while accepting the identical pattern in another language
  ("Саша Тест") moments later - loosened the prompt to be explicitly lenient, since a
  false rejection loses a real lead while a false acceptance just means an odd-looking
  name in the manager's inbox.
- **Valid emails were being rejected.** `extract_email` rejected any address whose local
  part had 6+ consecutive consonants (meant to catch keyboard-mashing like
  "asdfgh@x.com"), but it also rejected real addresses like `Vrnlsn@pm.me` - especially
  bad for this client base, since transliterated Slavic surnames cluster consonants
  often. Removed the heuristic; the existing syntax + domain checks are sufficient.
- **The weekend call-timing notice didn't fire for "Call me on Saturday."** Two
  compounding gaps in `is_asking_call_timing`: the call-word list only covered the
  теlefон/звон verb families ("зателефону", "позвон"), missing the separate Ukrainian
  дзвон root ("подзвоніть", "передзвоніть") entirely; and the check required an explicit
  "when"-word even when a weekend day was already named in the same message. Both fixed
  - a call/contact request that names a weekend day now gets the office-hours +
  weekend-closure notice without needing to also ask "when".

110 tests pass (91 + 19 new, across three new test files: `test_call_timing.py`,
`test_email.py`, `test_name_preamble.py`).

---

## 2026-08-27 07:55:24 +0200 — `6300779`
**Lead-capture flow redesign + final-review fix round (Czech pricing detection was completely broken)**

Branch `lead-capture-flow-redesign`: reworked the lead-capture funnel so a bare
"consultation" request is disambiguated (legal vs. visa/migration) before pricing is
shown, and — once pricing has been shown — the bot asks an explicit
yes/no "would you like our manager to contact you?" confirmation gate before it starts
collecting name/phone/email, instead of jumping straight into the form. Also added a
universal call-timing fast-path ("when will you call me?") wired into both `chat` and
`lead_capture`, which now prepends a weekend-office-hours notice when asked on a
Saturday/Sunday.

This commit is the final whole-branch review's fix round on top of that redesign,
covering four issues:

- **Czech pricing was never detected as shown, blocking 100% of Czech-language leads.**
  `FormValidator.has_price_been_shown` only matched the literal substring `"CZK"`, but
  `company_info.md`'s Czech section quotes every price in `Kč`, never `CZK` — so the
  confirmation gate above was never reached for Czech conversations, and the funnel
  looped forever re-explaining pricing instead of ever asking for a name. Fixed to match
  case-insensitively against both `"czk"` and `"kč"`.
- `SERVICE_LOCALIZED_NAMES` had no entry for `consultation_ambiguous`, leaking the raw
  internal ID to clients and to the manager's Telegram alert. Added localized names for
  all 4 languages.
- `CONTACT_CONFIRMATION_PROMPT` told users to reply "Yes" with their name and phone
  number, but the handler only accepts a bare yes/no — a compliant reply got stuck in a
  reprompt loop. Dropped the mismatched instruction from all 4 languages.
- The shared affirmative/negative word lists (`affirmation.py`) were a fail-soft
  optimization in `gate.py` but are now also load-bearing at the confirmation gate above,
  a fail-hard position: common affirmatives ("ok", "добре", "sure", …) were missing
  entirely, and `is_negative`'s prefix matching false-positived on Czech "nevím"/"nemám
  čas" (both start with "ne"), silently wiping the user's in-progress form. Widened the
  affirmative word set and switched `is_negative` to whole-first-token matching.

91 tests pass (85 pre-existing + 6 new regression tests for this fix round).

---

## 2026-08-26 22:32:25 +0200 — `277ff3c`
**Policy: manager is only notified for explicit human requests or completed leads, not for hostility alone**

User-directed policy change: "Manager should only be informed in two cases: when the client
specifically asks to speak with a human, or when the client confirms that they want to be
contacted and provides their contact details." Both cases already funnel through the existing
`gate` → `lead_capture` flow, which only notifies once contact details are captured.

Removed the aggressive-message Telegram alert from `gate.py` — both the LLM-classified path and
the mid-form regex fast path added earlier *this same session* specifically to preserve it (a
direct reversal of that earlier decision, at the user's explicit request). `is_aggressive` is
still detected and logged for visibility, just no longer pings staff on its own.
`notify_manager_aggressive_telegram` in `notify_stuff.py` is left in place but now has no caller.
Tests and `CLAUDE.md` updated to match (also corrected an inaccuracy caught in passing:
`notify_manager_media_telegram` is still actively used for media uploads, unaffected by this
change).

---

## 2026-08-26 22:21:39 +0200 — `5880de1`
**Prompt fix: chat was summarizing service options down to 1-2, omitting real priced variants**

User reported: asking "Potřebuju právníka" (a general need-statement) got a reply listing only
the 2 standard consultation durations, omitting the JUDr. Ulyana Kurivchakova option that's
equally present in `company_info.md`. The data was correct (just fixed in the previous entry);
the LLM chose to summarize rather than enumerate.

Added an explicit business rule to `prompts/chat.py`: when discussing a service with multiple
priced options, list every variant with its own price, even for a general query. This is
prompt-following, not deterministic logic — can't be meaningfully unit tested, needs a live
retest of the same query to confirm it actually changed the model's behavior.

---

## 2026-08-26 22:10:28 +0200 — `3307e1c`
**Content correction: JUDr. Ulyana Kurivchakova consultations are online or in-person, not in-person only**

The user spotted the bot stating "in-person only" for her 60-min consultation while testing — actually
available either way. First real content edit to `src/assets/company_info.md` since it was introduced:
fixed the one incorrect fact in all 4 languages, in the single place it lives; no other copy of it exists
anywhere else in the repo (confirmed by grep) — exactly the point of consolidating company info into one
file.

---

## 2026-08-26 22:00:10 +0200 — `f329040`
**Fix `**bold**` markdown not rendering — showed as literal asterisks in the chat**

Every response string (`MESSAGES`, `*_REPROMPT`, `company_info.md`, and what the `chat` LLM
naturally produces) writes `**bold**` — CommonMark-style, double asterisk. But
`message.py`'s `handle_text_message` sent every AI conversation reply with no `parse_mode` at
all, so Telegram displayed the raw text unrendered, asterisks and all. User noticed and asked
why replies didn't read like a normal LLM chat.

The obvious fix (`parse_mode="Markdown"`) would still have been wrong: Telegram's own
Markdown/MarkdownV2 modes use single `*bold*`, not `**bold**` — verified against aiogram's own
markdown helper before shipping anything. MarkdownV2 also requires escaping most punctuation in
every message or Telegram rejects it outright, too risky for unpredictable LLM output.

Fix: bot-level default `parse_mode=HTML` (matching the convention already used elsewhere —
media replies, staff notifications), plus a small converter applied at the one send call for AI
conversation replies: escapes `<`, `>`, `&`, then turns `**bold**` into real `<b>bold</b>` tags.

Found but not yet fixed: `/help`'s static text has the identical `**bold**` bug (plus
`_italic_`, which happens to render correctly under its own explicit `parse_mode="Markdown"`) —
lower-traffic than the main conversation flow, flagged for the user to decide on separately.

---

## 2026-08-26 18:12:31 +0200 — `de6c2e1`
**Fix two crashes in lead_capture that silently dropped completed leads**

Both pre-existing (out of scope for the graph refactor, `lead_capture.py`'s logic was untouched
there), and both fired for real on a live test lead — name and phone already captured, manager
never notified.

1. `_step_awaiting_email`'s invalid-email reprompt referenced `state.msg["ask_email"]` —
   `AgentState` has no `msg` field. Crashed uncaught the moment an email failed
   `FormValidator`'s validation (a gibberish test address rejected by the consonant-run
   heuristic). Added `EMAIL_REPROMPT` to `agent_rules/strings.py`, following the existing
   `PHONE_REPROMPT`/`NAME_REPROMPT` pattern exactly.
2. The success branch (valid email, or skip) called `notify_manager_lead_telegram(...,
   user=state.incoming.user, ...)` — `IncomingMessage` has no `user` field at all (it's a
   channel-agnostic schema). This meant **every** successfully completed lead crashed right
   before the manager notification, independent of bug 1. Fixed with `getattr(state.incoming,
   "user", None)`, matching the identical defensive pattern the old (now-deleted) `escalation.py`
   already used for this exact call.

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
