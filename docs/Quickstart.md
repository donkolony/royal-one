# Backend Quickstart

How to set up, run, test and deploy the Royal Square backend. Frontend setup is not covered here.

**What is verified.** Everything marked **Verified** was run on the development machine (Linux, Python 3.10.12). Section 5 (Supabase and Gemini) has since been run against a real project and is now verified; Groq and Render have not been tried. Anything still marked **Confirm** follows vendor conventions but has not been run, so read the vendor's current documentation and expect to adjust.

Related: [`api.md`](api.md) (the API contract) · [`ARCHITECT.md`](ARCHITECT.md) (design and verification status) · [`PRD.md`](PRD.md)

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Python **3.10 or newer** | **Verified** with 3.10.12. The code avoids 3.11-only features. |
| `git`, `curl` | |
| For the hosted setup | A Supabase project (URL, service-role key, database connection string) and an LLM key (Groq and/or Gemini). **Not needed** for offline development (Section 4). |

---

## 2. Create and activate the virtual environment: always first

**Nothing is installed until the virtual environment exists and is active.** This keeps project packages out of the system Python.

**Verified:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows (untested): .venv\Scripts\Activate.ps1
which python                       # must point inside backend/.venv/
pip install --upgrade pip
pip install -r requirements-dev.txt   # runtime + tests. Production needs only requirements.txt
```
If `which python` does not show `.venv`, stop and activate again. `.venv/` and `.env` are already in `.gitignore`. Leave the environment with `deactivate`.

`requirements.txt` pins the exact versions that passed the test suite (fastapi 0.141.1, pydantic 2.13.5, psycopg 3.3.6, supabase 2.31.0, and so on). Re-pin after any upgrade and re-run the tests.

---

## 3. Configuration (`backend/.env`)

```bash
cp .env.example .env               # then edit. NEVER commit .env or paste its contents anywhere
```
The app refuses to start, naming every missing variable, if a required one is unset. `.env.example` documents each variable; the important ones:

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | yes | Postgres connection string. |
| `AUTH_MODE` | no | `supabase` (default) or `local_hs256` (offline development and tests). |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` | if `AUTH_MODE=supabase` or `STORAGE_BACKEND=supabase` | The service-role key is server-side only. Never expose it to the browser. |
| `SUPABASE_JWT_SECRET` | if `AUTH_MODE=local_hs256` | Shared secret for local token signing. |
| `STORAGE_BACKEND` | no | `supabase` (default) or `memory` (offline development; files vanish on restart). |
| `LLM_PROVIDER`, `LLM_FALLBACK_PROVIDER` | no | `groq`, `gemini` or `none` (default). |
| `GROQ_API_KEY`, `GROQ_MODEL` / `GEMINI_API_KEY`, `GEMINI_MODEL` | if that provider is selected | Model names are never defaulted: take them from the provider's current documentation. |
| `ALLOWED_ORIGINS` | no | Comma-separated frontend origins, exact match (default `http://localhost:5173`). |
| `MAX_UPLOAD_BYTES`, `MAX_ATTACHMENTS_PER_CLAIM`, `MAX_ATTACHMENTS_PER_REQUEST`, `SIGNED_URL_TTL_SECONDS`, `ASSISTANT_RATE_LIMIT_PER_MIN`, `LLM_TIMEOUT_SECONDS`, `DB_POOL_MIN`, `DB_POOL_MAX` | no | Limits, with the defaults shown in `.env.example`. |
| `SEED_DEMO_PASSWORD` | only for `seed.py --auth` | Password for the demo Supabase Auth users. Choose your own. |

The frontend has its own variables (see the README). The backend never uses the anon key.

---

## 4. Path A: offline development (no Supabase, no LLM key)

**Verified.** Runs everything except real Supabase and real LLMs, on a local PostgreSQL bundled by the `pgserver` dev package.

```bash
# in backend/, venv active
python scripts/dev_db.py                 # starts Postgres, applies migrations, prints DATABASE_URL=...
```
Put that `DATABASE_URL` in `.env`, together with:
```
AUTH_MODE=local_hs256
SUPABASE_JWT_SECRET=<any random string of 32+ characters>
STORAGE_BACKEND=memory
LLM_PROVIDER=none
```
Then:
```bash
python scripts/migrate.py                # safe to re-run: "nothing (already up to date)"
python scripts/seed.py --reset           # synthetic demo data (Section 6)
python scripts/ingest_docs.py            # indexes the 4 synthetic PDFs in data/rag-docs/
uvicorn app.main:app --reload --port 8000
python scripts/make_token.py client1@demo.example     # prints a token for a demo user
python scripts/dev_db.py --stop          # when finished
```
Try it:
```bash
TOKEN=$(python scripts/make_token.py client1@demo.example)
curl -s localhost:8000/health
curl -s localhost:8000/api/v1/me -H "Authorization: Bearer $TOKEN"
curl -s localhost:8000/api/v1/me/dashboard -H "Authorization: Bearer $TOKEN"
```
Interactive docs: `http://localhost:8000/docs`. Without an LLM configured, assistant questions that match a document return `503 llm_unavailable`, and questions that match nothing return the "not found in the approved documents" answer.

---

## 5. Path B: Supabase and real LLMs (**Verified** with Supabase and Gemini; Groq not tried)

Run for real on 19 Sep 2026. Two things to know: Gemini's free tier has a small **daily** request cap per model (it was exhausted during testing, and the API then answers `429 RESOURCE_EXHAUSTED`), so keep the demo's quota in reserve and configure a fallback provider; and the dashboard menu names below are from memory.

1. Create a Supabase project. In `.env` set `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `DATABASE_URL`. Confirm in the project settings whether to use the direct or the pooled connection string for your host (the direct host may be IPv6 only). The app already disables prepared statements so it works behind a transaction-mode pooler.
2. `python scripts/migrate.py`. This creates the tables, enables row-level security everywhere (default deny), and tries to create the private buckets `attachments` and `rag-docs`. If the log says the buckets could not be created in SQL, create two **private** buckets with those names in the Supabase dashboard.
3. `python scripts/seed.py --reset --auth`. `--auth` creates the demo users in Supabase Auth first (profiles reference `auth.users`, so on Supabase the users must exist before the data). Set `SEED_DEMO_PASSWORD` first. Users are created with fixed ids so the seeded data lines up.
4. `python scripts/ingest_docs.py` (uploads the PDFs to the `rag-docs` bucket).
5. Set `AUTH_MODE=supabase`, `STORAGE_BACKEND=supabase`, and the LLM variables. Run one real assistant question and one real email draft before relying on them. The Gemini request format is **verified live**; the Groq one is **not** (no Groq key has been tried).
6. To call the API as a demo user, sign in through Supabase Auth exactly as the frontend does and send the access token as `Authorization: Bearer <token>`.

---

### Where to find each value (**Confirm**: dashboard menu names are from memory and may have moved)

| Value | Where to get it |
|---|---|
| `SUPABASE_URL` | Supabase dashboard, your project, **Project Settings > API** (or the **Connect** button). Looks like `https://<project-ref>.supabase.co`. |
| `SUPABASE_SERVICE_ROLE_KEY` | Same area, **API Keys**. You need the **secret** key (`sb_secret_...`) or, on older projects, the legacy `service_role` key. **Not** the publishable/anon key: the backend checks for that at startup and refuses it. Server-side only: never put it in the frontend, chat or Git. |
| Publishable (anon) key | Same page. This one is for the **frontend** (`VITE_SUPABASE_ANON_KEY`). Not used by the backend. |
| `DATABASE_URL` | Dashboard **Connect** button, the *connection string* for Postgres (the "Session pooler" string is the safest choice when your host has no IPv6; the *Direct* one may be IPv6 only). It looks like `postgresql://postgres.<project-ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:5432/postgres`. Replace `<PASSWORD>` with the database password. If you forgot it: **Project Settings > Database > Reset database password**. If the password contains special characters (`@ : / ? # %`), URL-encode them (for example `@` becomes `%40`). |
| `SEED_DEMO_PASSWORD` | You choose it: any password of at least 8 characters. It is given to the six demo users so you can sign in as them. |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Google AI Studio (aistudio.google.com), API keys. List the models your key can use with a request to the models endpoint, or read the model names in AI Studio; set one that supports `generateContent`. |
| `GROQ_API_KEY` / `GROQ_MODEL` | console.groq.com, API Keys (keys start `gsk_`). Pick a current model from Groq's model list. Optional: only needed if you want a fallback for Gemini. |

## 6. Demo data

`python scripts/seed.py --reset` creates (all synthetic; emails use the reserved `.example` domain):

| Who | Login | Notes |
|---|---|---|
| Adviser | `adviser@demo.example` | Has 3 clients. |
| Second adviser | `adviser2@demo.example` | Has 1 client; used to prove advisers cannot see each other's data. |
| Client One | `client1@demo.example` | 4 policies, net worth, 3 goals (one shared), a submitted claim, a private draft claim, 2 open requests. |
| Client Two | `client2@demo.example` | A claim in assessment (claim number `SC-778201`), a consultation request. |
| Client Three | `client3@demo.example` | A claim in repair for over a week with a hire car (triggers the "stale claim" alert); an expired licence (overdue reminder). |
| Client Four | `client4@demo.example` | Belongs to the second adviser. |

The seed also creates three simulated emails for the adviser (one from an insurer, one from a client, one newsletter). Dates are relative to today so reminders always have something to show. Ids are derived deterministically from names, but the frontend must never hardcode them.

---

## 7. Run the tests

**Verified:** 367 tests, about one minute, no internet or Supabase needed (a real PostgreSQL is started automatically by `pgserver`).
```bash
pytest                       # everything
pytest tests/test_claims.py  # one area
python -m pyflakes app tests # lint (pip install pyflakes)
```
What they cover: the whole API contract (`test_contract.py` fails if the code and `docs/api.md` disagree), cross-client and cross-adviser isolation, the claim state machine, uploads, reminders, requests, the assistant's grounding guarantees (including prompt-injection and fabricated-citation cases), email flags and drafts, the LLM adapters against mocked HTTP, and the migrations. Tests never read your `.env`.

---

## 8. Deploy (Render) (**Confirm**)

| Setting | Value |
|---|---|
| Service type | Web service |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (the command itself is **verified** locally; that Render supplies `PORT` needs confirming) |
| Health check path | `/health` |
| Python version | Match your local version (3.10+). Confirm how Render selects it. |
| Environment | Every required variable from Section 3, set in Render's dashboard, with `AUTH_MODE=supabase` and `STORAGE_BACKEND=supabase`. Set `ALLOWED_ORIGINS` to the Vercel URL. |

Run migrations, seeding and ingestion from your own machine against the Supabase database; they are not run at boot.

**Before every demo:** `scripts/warm_backend.sh https://<backend-host>` (waits for a sleeping free-tier service to wake), then load one authenticated page and ask the assistant one question.

---

## 9. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Packages installed somewhere unexpected | The venv was not active. `deactivate`, redo Section 2, check `which python`. |
| App exits at startup naming variables | Those variables are missing from `.env`. |
| `uvicorn: Attribute "app" not found` | Run it from the `backend/` folder so that `app.main` is importable. |
| CORS error in the browser | The frontend origin is not in `ALLOWED_ORIGINS` (must match scheme, host and port exactly). |
| Every call returns `401 token_invalid` | With `AUTH_MODE=supabase`: the frontend is signed in to a different project than the backend, or the token verification setup needs checking. With `local_hs256`: the token was signed with a different secret. |
| `403 forbidden` right after login | The auth user has no `profiles` row: seed with `--auth` (Supabase) or check the user id. |
| `seed.py` fails with a foreign-key error on Supabase | Use `--auth` so the users exist before the data. |
| Database connection fails from the hosted service only | The connection string points at a host the platform cannot reach (direct vs pooled). |
| Assistant returns `503 llm_unavailable` | No LLM is configured, or both providers failed or were rate limited. Check keys and model names; wait `retry_after_seconds`. |
| Assistant says "I couldn't find this in the approved documents" | Working as designed when nothing relevant is indexed. Run `scripts/ingest_docs.py`; try a question that uses words from the documents. |
| First request after idle is slow | Free-tier cold start. Use the warm-up script. |
| Uploads return `415` | The file's real content does not match its declared type, or the type is not allowed for that `kind`. Use JPEG, PNG, WebP or PDF (audio for voice notes). |

---

## 10. Working rules for anyone changing the backend

1. Create and activate the virtual environment before installing anything.
2. Change [`api.md`](api.md) in the same change as any route or shape change and add a changelog line. `pytest` fails if the index and the code drift.
3. Never commit secrets or `.env` files. Never log tokens, request bodies, bank details, email text or document text.
4. Verify a library or external API in the venv or its official documentation before relying on it, and mark anything unverified as such.
5. Keep synthetic data labelled as synthetic.
6. Run `pytest` before pushing.
