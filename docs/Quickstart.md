# Backend Quickstart

How to set up, run and check the Royal Square backend on a development machine. Frontend setup is not covered here.

**Read this first: what is verified and what is not.**

| Marker | Meaning |
|---|---|
| **Verified** | Run on the development machine (Linux, Python 3.10.12) while writing this document. |
| **Planned** | Describes files and commands that do not exist yet. They will work once the scaffold phase (`ARCHITECT.md` §14, Phase 0) is done. Treat any failure as a bug in the scaffold or in this document. |
| **Confirm** | Depends on an external service's current documentation, which has not been checked. Read the official docs first. |

Related documents: [`api.md`](api.md) (the API contract), [`ARCHITECT.md`](ARCHITECT.md) (design and build order), [`PRD.md`](PRD.md) (requirements).

---

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Python **3.10 or newer** | **Verified:** `python3 --version` reports 3.10.12 on the dev machine, and `python3 -m venv` works there. The code must not use 3.11-only features. |
| `git` | |
| A Supabase project | You need its URL, the service-role key, the database connection string, and (for the frontend only) the anon key. |
| An LLM API key | Groq (primary) and/or Gemini (fallback). |
| `curl` | For the smoke tests below. |

---

## 2. Create and activate the virtual environment — always first

**Rule: nothing is installed until the virtual environment is created and activated.** This keeps project packages out of the system Python.

**Verified** (Linux/macOS):
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```
Windows (PowerShell): `.venv\Scripts\Activate.ps1` (**Planned**, not tested).

Check that it is active before any `pip install`:
```bash
which python        # must point inside backend/.venv/
python --version    # 3.10.x or newer
pip --version       # must also point inside backend/.venv/
```
If `which python` does not show `.venv`, stop and activate again. `.venv/` is already in `.gitignore`.

To leave the environment: `deactivate`.

---

## 3. Create the `.env` file

**Planned.** `backend/.env.example` is created in the scaffold phase.

```bash
cp .env.example .env        # run inside backend/
```
Then fill in the values below. `.env` is in `.gitignore`; **never commit it**, never paste its contents into chat, issues or docs.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `ENVIRONMENT` | no | `development` (default) or `production`. |
| `LOG_LEVEL` | no | `INFO` (default). |
| `SUPABASE_URL` | yes | Supabase project URL. |
| `SUPABASE_SERVICE_ROLE_KEY` | yes | Server-side key. **Never expose to the browser.** |
| `DATABASE_URL` | yes | Postgres connection string from the Supabase project. **Confirm** which host to use (direct or pooled) from the project's settings. |
| `LLM_PROVIDER` | yes | `groq` or `gemini`. |
| `LLM_FALLBACK_PROVIDER` | no | The other provider, used when the primary fails. |
| `GROQ_API_KEY`, `GROQ_MODEL` | if using Groq | The model name is **not** hardcoded. **Confirm** current models in Groq's documentation. |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | if using Gemini | As above. |
| `EMAIL_PROVIDER` | no | `mock` (default). `gmail` is reserved and not built. |
| `ALLOWED_ORIGINS` | yes | Comma-separated frontend origins, e.g. `http://localhost:5173`. |
| `MAX_UPLOAD_BYTES` | no | Default 10485760 (10 MB). |
| `SIGNED_URL_TTL_SECONDS` | no | Default 600. |
| `ASSISTANT_RATE_LIMIT_PER_MIN` | no | Default 10 per user. |
| `ATTACHMENTS_BUCKET`, `RAG_DOCS_BUCKET` | no | Storage bucket names; defaults `attachments` and `rag-docs`. |

The frontend has its own variables (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL`); see the README. The backend never needs the anon key for data access.

The app fails at startup, naming the variable, if a required one is missing.

---

## 4. Install dependencies

**Planned.** Run only with the virtual environment active (Section 2).

```bash
pip install --upgrade pip
pip install -r requirements.txt
```
The expected dependency set is described in `TECHSTACK.md`. `requirements.txt` will be generated in the scaffold phase and **pinned to the versions actually installed and tested in the venv**, not to versions copied from documentation.

---

## 5. Set up the database

**Planned.**

1. Create a Supabase project (Supabase dashboard).
2. Put its connection string in `DATABASE_URL` (Section 3).
3. Apply the migrations in `supabase/migrations/` in order:
   ```bash
   python scripts/migrate.py
   ```
   The script records applied files in a `schema_migrations` table and is safe to re-run.
4. Load the synthetic demo data:
   ```bash
   python scripts/seed.py
   ```
   The seed creates one adviser, a few clients with policies, goals, reminders, one claim in each interesting status, requests, and simulated email threads. It also creates the matching Supabase Auth users. **Credentials are printed by the script once and are never committed.** All data is synthetic.
5. Index the assistant's documents:
   ```bash
   python scripts/ingest_docs.py
   ```
   Source PDFs and `manifest.json` live in `data/rag-docs/`. Demo documents are labelled synthetic.

---

## 6. Run the API

**Planned.**
```bash
uvicorn app.main:app --reload --port 8000
```

Smoke tests (with the server running):
```bash
curl -s http://localhost:8000/health
# expected: {"status":"ok","version":"0.1.0","time":"…"}

curl -s http://localhost:8000/api/v1/meta | head -c 300
# expected: JSON containing "api_version":"v1"

curl -s -i http://localhost:8000/api/v1/me
# expected: HTTP 401 with {"error":{"code":"unauthenticated",…}}
```
Interactive documentation: `http://localhost:8000/docs`. OpenAPI JSON: `http://localhost:8000/openapi.json`.

### Calling authenticated endpoints

Obtain an access token by signing in with a seeded user through Supabase Auth (the same way the frontend does). **Confirm** the exact sign-in request against the current Supabase Auth documentation; the seed script will also offer a helper that prints a token for a chosen demo user.
```bash
TOKEN="<access token>"
curl -s http://localhost:8000/api/v1/me -H "Authorization: Bearer $TOKEN"
```

---

## 7. Run the tests

**Planned.**
```bash
pytest -q
```
Unit tests use fake Supabase and fake LLM providers and need no internet. The tests that matter most for the demo are the authorization suite and the RAG guarantees (see `ARCHITECT.md` §12).

---

## 8. Deploy (Render)

**Planned; Confirm every item against Render's current documentation.**

| Setting | Value |
|---|---|
| Service type | Web service |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/health` |
| Python version | Set it to match your local version (3.10+). **Confirm** how Render selects the Python version. |
| Environment | Every required variable from Section 3, entered in Render's dashboard. Set `ALLOWED_ORIGINS` to the Vercel URL. |

Run migrations from your machine against the Supabase database (Section 5) before the first deploy. They are not run at boot.

**Before every demo:** run `scripts/warm_backend.sh` (planned) so the first request is not slow, then open `/health` and one authenticated page.

---

## 9. Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `pip install` puts packages somewhere unexpected | The venv was not active. Run `deactivate`, then Section 2, and check `which python`. |
| App exits at startup naming a variable | A required variable is missing from `.env`. |
| Browser shows a CORS error | The frontend origin is not in `ALLOWED_ORIGINS` (must match exactly, including port and scheme). |
| Every call returns `401 token_invalid` | Token verification is misconfigured (`ARCHITECT.md` §4.2), or the frontend is signed in to a different Supabase project than the backend. |
| `403 forbidden` right after login | The auth user has no row in `profiles` (not seeded). |
| Database connection fails from the hosted service only | The connection string points at a host the platform cannot reach. **Confirm** the direct vs pooled host in the Supabase project settings. |
| Assistant returns `503 llm_unavailable` | Both providers failed or were rate limited. Check keys and model names; wait for `retry_after_seconds`. |
| First request after idle takes long | Free-tier cold start. Use the warm-up script. |

---

## 10. Working rules for anyone changing the backend

1. Create and activate the virtual environment before installing anything.
2. Update [`api.md`](api.md) in the same change as any route or shape change, and add a changelog line. The frontend team builds against it.
3. Never commit secrets or `.env` files. Never log tokens, bodies, bank details, email text or document text.
4. Verify a library or external API in the venv or its official documentation before designing around it, and mark anything unverified as such.
5. Keep synthetic data labelled as synthetic.
