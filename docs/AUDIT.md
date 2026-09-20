# Audit: Royal Square Revenue & Compliance Operating System

| | |
|---|---|
| **Date** | 20 September 2026 |
| **Scope** | The repository as found (`main`, commit `41d9793`), before any feature work |
| **Method** | Read `issue.md`, all project docs, all backend source, the migrations, the seed, the tests and the frontend source. **Ran** the baseline: `pytest`, `tsc`, `vite build`, and the real backend plus the real frontend in headless Chrome against an isolated local Postgres. Nothing here was run against the Supabase project in `backend/.env`. |
| **Status labels** | **Verified** = observed by running it. **Read** = seen in code, not run. **Unverified** = cannot be established from this environment. |

## 0. Read this first

1. **Several features the brief expects to exist do not exist in this repository.** The brief says to "expect" an insurer simulator, a compliance file, an adviser cockpit, gap flags and a goal what-if. None of these is in the code (searched backend and frontend; **Verified**). What exists is the backend described in `docs/ARCHITECT.md` (claims, requests, goals, reminders, RAG, mock email) and a frontend of which **9 of 18 pages crash against the real backend** (section 3, R1). The audit and the build order below are based on what is really there.
2. **Rule conflicts** (you asked me to say so and follow the stricter rule):

   | Rule | Conflicts with | Resolution |
   |---|---|---|
   | `AGENTS.md` §2.1: "do not create, edit or delete anything under `frontend/`", scope "backend only" | This task needs an owner UI, a radar UI and repairs to broken pages; you also wrote "you have full control on the current dir" | Your explicit, later instruction wins. Without touching `frontend/` the task cannot be done. `AGENTS.md` is updated at the end to say so. |
   | `AGENTS.md` §2.9: "do not commit or push unless asked" | "commit after each section" | Local commits after each section, as asked. **Nothing is pushed.** |
   | `docs/ARCHITECT.md` §4.4: RLS is enabled with **no** policies (default deny) | Brief H: per-role RLS policies and tests that attempt cross-client access | The brief is stricter. Real policies are added and tested (build step 1). |
   | `docs/ARCHITECT.md` §17 and `docs/api.md` §1.9: no admin UI, no Supabase Realtime, no WebSockets | Brief B (owner view) and G (near-live updates) | An owner role and views are added. Live updates use short polling: every read goes through the API and the tables are default-deny, so Supabase Realtime would receive nothing. |
   | `docs/PRD.md` §4.3 and §6: Admin is "future" | Brief B | A new `owner` role is added (there is no existing admin role in the schema). |

3. **Machine note.** The system `node` is **v12.22.9**, which cannot run Vite 5. I used a Node 20 copy in a scratch directory. `tsc --noEmit` passes and `vite build` succeeds under Node 20 (**Verified**). The README should state the minimum Node version (done in the final docs pass).

## 1. Already implemented

| Feature | Where | Evidence |
|---|---|---|
| Auth (Supabase JWT, role from `profiles`), client and adviser scoping | `backend/app/core/auth.py`, `services/common.py` | 17 authorisation tests pass (**Verified**) |
| Client dashboard, net worth, policies, financial items | `services/dashboards.py`, `finance.py`, `catalog.py`; UI `pages/client/Dashboard.tsx` | Backend tests; the client dashboard renders (**Verified**) |
| Goals with progress %, shared goals | `services/goals.py` | Backend tests. Client Goals page **crashes** (R1) |
| Reminder engine (computed on read, idempotent, 7 rule types) | `services/reminders.py` | 21 tests. Client and adviser reminder pages **crash** (R1) |
| Motor claim: draft, checklist, uploads, submit, adviser pipeline, 9-state machine, hire car, repair, review, per-claim timeline | `services/claims.py`, `routes/claims_routes.py` | 41 tests. Adviser pipeline and claim detail render (**Verified**); the client accident checklist **crashes** (R1) |
| Client requests (7 types, config-driven field definitions, server validation) | `domain/constants.py` `REQUEST_TYPES`, `services/requests.py` | 13 tests. Client requests page **crashes and is a stub** (R1, R2) |
| Private storage, signed URLs, upload size and content-signature checks | `storage/`, `services/attachments.py` | Tests on both |
| RAG assistant: FTS retrieval, refusal, validated citations (document, page, quote) | `services/assistant.py`, `rag/` | 46 tests on synthetic corpus. The page renders (**Verified**); answering with a real LLM **Unverified** here |
| Mock email adapter and draft assistant | `email/` | 21 tests. Page renders (**Verified**) |
| Migrations, seed, offline dev DB, contract test tying `docs/api.md` to the routes | `supabase/`, `app/seed.py`, `backend/scripts/`, `tests/test_contract.py` | **367 tests pass** on a real bundled PostgreSQL (**Verified**, baseline) |

**Not present (despite the brief):** insurer simulator, compliance file, adviser cockpit, gap flags, goal what-if, audit log, identity vault, opportunity detection, owner role, notifications, advice records, consents, retention rules, privacy page, live updates beyond a 30-second refetch on two claim pages.

## 2. Gap analysis against `issue.md`

**Done / Partial / Missing** describes the repository as found.

### 2.1 The five problem areas

| Requirement | Status | Files involved | What is needed |
|---|---|---|---|
| **1a** Claim starts, system knows which documents/photos are needed and collects them step by step | Partial | `constants.CHECKLIST`, `claims.missing_fields`, `pages/client/RegisterClaim.tsx` | Backend has the checklist and `missing_fields`. Move onto a config-driven workflow engine with steps and required documents; repair the client pages. |
| **1b** Status updates flow between client, adviser and (later) insurer | Partial | `claims.add_event`, `ClaimTracking.tsx` (30 s refetch) | No notifications, no insurer side. Add in-app notifications, an insurer simulator (demo adapter), faster polling. |
| **1c** Address change, policy document, IRP5, border letter as one-click or short forms | Partial | `REQUEST_TYPES`, `pages/client/Requests.tsx` | Types exist in the backend; the UI is a stub with placeholder text. Build the generic form renderer on the workflow engine. |
| **2a** Every advice interaction, claim update, document exchange logged with timestamp, user, context | **Missing** | `claim_events` only (claims only) | Append-only `audit_log`, written from the service layer. |
| **2b** Clean, searchable audit trail | **Missing** | none | Search, filter, CSV/PDF export, hash chain. |
| **2c** RAG with page references | Done (backend), Partial (UI) | `services/assistant.py`, `Assistant.tsx` | Add source filters, "show source passage", query audit, offline fallback, labelling of the demo corpus. |
| **3a** Capture verified ID once, store securely | **Missing** | none | Identity vault with private bucket, verification metadata, `IdentityVerifier` demo adapter. |
| **3b** Re-use across claims, applications, reviews | **Missing** | none | Reuse in claim and request flows plus a reuse log. |
| **3c** Flag expiring documents, trigger reminders | Partial | `reminders.py` `licence_expiry` (from a date field only) | Extend to vault documents, notify the adviser, add compliance flag and radar touchpoint. |
| **4a** One source of truth; client and adviser see the same live data | Partial | Same API serves both roles (good) | Per-client timeline, fast polling on every shared screen. |
| **4b** Nothing important lives only in email or WhatsApp | **Missing** | none (requests have one-line responses; claims have notes) | In-app message thread per client. |
| **5a** Access controls: client own data, adviser own clients | Done at API level | `auth.py`, `common.py`, `test_authorization.py` | Add database-level per-role RLS policies and tests (currently default-deny, no policies). |
| **5b** Secure storage, controlled sharing | Done | private buckets, 600 s signed URLs | None. |
| **5c** Audit of who accessed what | **Missing** | none | Log staff views and downloads; log denied attempts. |
| **5d** Minimal data, clear retention rules | Partial | No national ID number column (good) | Documented retention config plus a "past retention" review list; privacy page. |

### 2.2 The owner's six needs

| Owner need | Status | What is needed |
|---|---|---|
| Advisers spend time advising and selling, not on forms | **Missing** | Workflow engine, identity reuse, and a productivity view (labelled as a model, not a stopwatch). |
| Accident handling controlled by Royal Square | Partial | Pipeline exists. Add notifications, insurer simulator, live timeline. |
| Compliance happens almost automatically | **Missing** | Audit log, advice records, consents, compliance pack, health score. |
| See opportunities without digging | **Missing** | Opportunity Radar and owner aggregates. |
| Clean records to answer a regulator or insurer fast | **Missing** | Compliance pack (PDF/JSON) plus audit export. |
| Retain clients, sell more products per client | **Missing** | Client health, retention indicators, products-per-client, goal-slipping nudges. |

### 2.3 The five revenue levers

| Lever | Status | Delivered by (planned) | Proving metric |
|---|---|---|---|
| 1. More time selling | **Missing** | Workflow engine, identity reuse | Admin tasks automated and modelled minutes avoided |
| 2. Cross-sell / up-sell | **Missing** | Opportunity Radar | Opportunities surfaced → actioned → won, estimated value |
| 3. Retention | **Missing** | Client health, review reminders, goal nudges | Clients at risk, overdue reviews, contact recency |
| 4. More clients per adviser | **Missing** | Workflows, notifications | Clients per adviser, average claim handling time |
| 5. Lower regulatory risk | **Missing** | Audit log, compliance pack, RLS | Compliance health score, open gaps |

## 3. Risks found

| # | Severity | Finding | Evidence |
|---|---|---|---|
| **R1** | **Critical** | **Nine pages crash against the real API** with `x.map is not a function`, because they treat list endpoints as arrays while the API returns `{items, total, limit, offset}`. Client: Requests, Accident checklist, Policies, Goals, Reminders. Adviser: Clients, Requests, Reminders. Adviser Client detail tabs (goals, financial items, reminders) silently show "empty". | **Verified** in headless Chrome |
| **R2** | High | Client Requests page renders the literal text `[ Dynamic Form Fields rendered here based on type.fields ]` and submits `{type, data: {}}`, but the API requires `payload`, so every submit would return 422. | **Read** (`pages/client/Requests.tsx:103,112`) |
| **R3** | High | Dead buttons (no handler): Client detail "Add Goal", "Add Item", "Add Reminder", "Mark Done"; adviser Reminders "Add Reminder"; claim detail line 197; client "Submit Review". | **Read** (grep) |
| **R4** | High | Adviser dashboard "Needs attention" links to `/${resource}/${id}` (for example `/claim/<id>`), which matches no route; the `kind` values it switches on (`overdue_reminder`…) are not what the API sends (`reminder`, `claim`…). | **Read** (`Dashboard.tsx:94-100`, `dashboards.py`) |
| **R5** | Medium | Design drift: 10 files use `slate`/`yellow` classes outside the navy/ruby brand palette; `any` in 14 files; headings such as "Dashboard \| Royal Square Adviser Portal". | **Read** |
| **R6** | Medium | `lib/mock.ts` (68 KB of fictional data) is in the production bundle and is used silently whenever `VITE_API_URL` is empty, so a mis-set deploy shows fake data. A "Dev Mode: Mock Data" banner mitigates but does not remove this. | **Read** |
| **R7** | High | No per-role RLS policies and no RLS tests. The API isolates correctly, but the database-level control the brief requires is absent. | **Read** (`0001_schema.sql`) |
| **R8** | High | No audit log, no access logging, no denied-attempt logging. | **Read** |
| **R9** | Medium | Repo hygiene: `venv-extract/` (765 files, 67 MB) is committed; generated `tsbuildinfo` and `vite.config.d.ts` are tracked; stray root scripts (`crop_*.py`, `extract_images.py`, `get_colors.py`), a 37 KB `frontend/src/generator.py`. | **Verified** (`git ls-files`) |
| **R10** | Info | **No secrets in tracked files** by a pattern scan for Supabase secret keys, Groq/Gemini/xAI keys, JWTs and database URLs with passwords (excluding `venv-extract`). `backend/.env`, `backend/.env_` and `frontend/.env.local` are gitignored and untracked. **Limit:** a pattern scan is not proof; I deliberately did not open the ignored env files. | **Verified**, limited |
| **R11** | Medium | The demo depends on an LLM whose free tier can return `429`/`503` (documented in `ARCHITECT.md` §0). Today a failed provider returns `503`, so the assistant page shows an error. The architecture doc lists a retrieval-only fallback that is **not implemented**. | **Read** (`assistant.py`) |
| **R12** | Low | Docs drift: README feature checklist is all unticked although the backend is built; `api.md`/tests hard-code "68" endpoints; `frontend/.env.example` and `backend/.env.example` need new variables. | **Read** |
| **R13** | Low | Known limits already documented: one DB connection held during an LLM call (pool of 8); in-process rate limiter and token cache (single instance). | **Read** (`ARCHITECT.md` §0) |
| **R14** | Info | Groq and Render paths remain unverified (no key, no deploy from here). Gemini was verified live on 19 Sep by the previous author. | Doc claim, **Unverified** here |

## 4. Assumptions (stated instead of asking)

- **Role:** a new `owner` role; the owner sees every client in the firm. Advisers keep seeing only assigned clients.
- **Live updates:** polling at 5 to 15 seconds, not Realtime (see section 0).
- **Money:** every rand figure is a **demo estimate** computed from `backend/app/domain/radar_config.py`. The assumptions (commission rates, premium per R1 million of cover, income multiple, minutes per admin task) are invented placeholders, are shown in the UI, and are not statements about real commissions or real productivity.
- **Insurer:** simulated behind an interface and labelled "Demo".
- **Identity:** verification is simulated behind `IdentityVerifier`. No KYC provider is called or claimed.
- **Retention period:** a configuration placeholder, to be set by counsel or the compliance officer. I am not asserting a legal period.
- **POPIA:** referenced by name only, as a regime for counsel to validate. Nothing here claims compliance.
- **New personal data:** `dependants` and `annual income` are added to the client record because the under-insurance rule needs them. They are optional, adviser-entered, and listed on the privacy page.
- **Where demo data lives:** one seed (`python scripts/seed.py --reset`) creates the whole demo, including a third adviser and an owner login. On Supabase, `--auth` creates their auth users.

## 5. Build order

Biggest revenue and risk impact first, subject to dependencies.

| Step | Section | Why here |
|---|---|---|
| 1 | **Foundation: `owner` role, `audit_log` (append-only, hash chain), per-role RLS policies and tests** (E core, H core) | Everything later writes audit rows; the owner view is gated by the role; the two "never cut" security items are proven first. |
| 2 | **A: Opportunity Radar** (rules, lifecycle, drafts, seed extension) | The largest revenue lever, and its seed data makes every later screen meaningful. |
| 3 | **B: Business Health** with client-health formula (owner home) | The owner's home screen; consumes A and the audit log. |
| 4 | **C: Workflow engine**, notifications, insurer simulator, plus repair of the crashing pages (R1 to R4) | Removes the paperwork pain and is needed for the claim demo; the crashing client and adviser pages are fixed here because these flows run through them. |
| 5 | **D: Identity vault and reuse** | Depends on the workflows (reuse) and feeds compliance and radar. |
| 6 | **E rest: advice records, consents, compliance pack, audit UI and export** | Turns the raw audit log into the regulator-ready deliverable. |
| 7 | **F: RAG hardening** (audit, filters, passage view, retrieval-only fallback) | Small, but it is a demo step and a known failure risk (R11). |
| 8 | **H rest: retention review, privacy page, `.env.example`, secrets check** | Closes the protection story. |
| 9 | **G: shared timeline, in-app messages, polling on all shared screens** | Cuttable polish per the brief; the core of G (same API for both roles) already exists. |
| 10 | **I: retention loops** (goal slipping creates a client nudge and an adviser opportunity) | First in the cut order. |
| 11 | **Docs and pitch:** README, PRD, TECHSTACK, DESIGN, AGENTS, CLAUDE, `BUSINESS_CASE.md`, demo script, final report | Required by the definition of success. |

Repo hygiene (R9) is handled with the first commit: `venv-extract/` is untracked (`git rm --cached`, files stay on disk) and ignored.
