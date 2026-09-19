# Agents and Roles

**Royal Square Financial — Client & Advisor Platform · AfriHack 2026**

This file describes who does what: the people, the AI agents that help build the system, and the AI features inside the product. `CLAUDE.md` holds the working role prompt for the AI coding assistant.

## 1. People

| Who | Owns |
|---|---|
| Frontend developer team | Everything under `frontend/`; integrates with the API through [`docs/api.md`](docs/api.md) |
| Backend owner (the user running this repo's backend work) | Everything under `backend/`, `supabase/`, `data/`, `scripts/`, and the docs in `docs/` |
| Royal Square Financial (client) | Requirements (`docs/Royal_Square_Financial_PRD.pdf`); confirms the interpretation questions in `docs/api.md` §8 |

## 2. AI coding agent (Claude Code)

**Scope for the current work: backend only.**

Rules the agent follows in this repository:

1. **Do not create, edit or delete anything under `frontend/`.** Frontend needs are met by keeping [`docs/api.md`](docs/api.md) accurate.
2. **`docs/api.md` is the contract.** Any change to a route, field, enum or rule is made in `api.md` first (or in the same change) and recorded in its changelog.
3. **Create and activate the Python virtual environment (`backend/.venv`) and the `.env` file before installing any dependency.** See [`docs/Quickstart.md`](docs/Quickstart.md).
4. **Requirements come from the PDF** (`docs/Royal_Square_Financial_PRD.pdf`). If a doc disagrees with the PDF, the PDF wins.
5. **Do not assert unverified facts.** Library names, APIs, model names, pricing, free-tier limits and vendor behaviour are verified (in the venv or the vendor's docs) before being relied on, and marked **Open** or **Confirm** in the docs until they are.
6. **No secrets in Git.** Keys live in environment variables only. Never print or log tokens, bank details, email bodies or document text.
7. **Synthetic data only**, labelled as synthetic. Nothing connects to Royal Square's production systems.
8. **Keep the MVP small.** Follow the build order in [`docs/ARCHITECT.md`](docs/ARCHITECT.md) §14. P2 endpoints may stay `501 not_implemented`.
9. **Do not commit or push unless asked.**

## 3. AI features inside the product

| Feature | Available to | What the model does | What deterministic code does |
|---|---|---|---|
| Document assistant (RAG) | Advisers | Writes a short answer from retrieved passages, citing them by number | Retrieves passages, refuses when nothing relevant is found, builds citations from stored text (document, page, quote), validates output |
| Email draft assistant | Advisers | Writes prose for a draft email | Supplies the facts from the database, removes any identifier not in those facts, always flags the draft for human review |

Neither feature can take actions: no sending email, no changing records. Document and email content is treated as untrusted data. Details: [`docs/ARCHITECT.md`](docs/ARCHITECT.md) §8 and §9.

## 4. File map

| File | Purpose |
|---|---|
| `CLAUDE.md` | Role prompt for the AI coding assistant |
| `AGENTS.md` | This file |
| `README.md` | Project overview |
| `docs/Royal_Square_Financial_PRD.pdf` | Client requirements (source of truth) |
| `docs/PRD.md` | Markdown copy of the PDF plus team notes |
| `docs/TECHSTACK.md` | Stack choices and their status |
| `docs/ARCHITECT.md` | Backend architecture, decisions, build order |
| `docs/api.md` | API contract for the frontend and the backend implementer |
| `docs/Quickstart.md` | Backend setup and run instructions |
| `docs/DESIGN.md` | Screens, flows and product design principles |
