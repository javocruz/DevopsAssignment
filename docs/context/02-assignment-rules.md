# 02 - Assignment rules (hard constraints)

Source: IE University DevOps, Individual Assignment 1. Deadline **2026-10-04 23:59**.
If a change would break anything here, stop and ask Javi.

## Hard requirements (never break these)

- Single process, single container. No microservices, no second repo, no separately deployed services.
- **SQLite** only, at one documented path: `DATA_DIR/edgebook.db`.
- Exactly **one** dependency manifest at the repo root: `requirements.txt`.
- **No** Dockerfile, `docker-compose.yml`, `.github/workflows/`, or any CI file.
- **No** Terraform, Bicep, ARM, or other IaC.
- **No** real public deployment.
- **No** external managed DB, cache, queue. No Redis, RabbitMQ, Celery, cron.
- Soft cap: ~12 third-party packages. Rough file count: 15 to 50 files (excluding venv, lockfiles).
  - Edgebook plan: ~46 files of code, tests, fixtures and required docs, plus 7 agent context files in `docs/context/` (~53 total). This is soft guidance. Do not add files beyond the plan in `03-architecture.md`.

## Deployment contract (§7), how Edgebook satisfies each

| # | Rule | How we meet it |
|---|---|---|
| 1 | One start command | `python app.py` |
| 2 | Bind `0.0.0.0` | `uvicorn.run(app, host="0.0.0.0", port=settings.port)` in `app.py` |
| 3 | Port from env var | `PORT`, default `8000` |
| 4 | No interactive setup | tables created in `db.init_db()` on startup, `CREATE TABLE IF NOT EXISTS` |
| 5 | SQLite at one path | `DATA_DIR` (default `./data`), file `edgebook.db`, folder auto-created. Only place the app writes, so A2 mounts one volume there |
| 6 | No required external dependency | defaults `MARKET_SOURCE=fixture`, `NEWS_SOURCE=fixture`, `DECIDER=stub`: zero network, zero keys |
| 7 | One manifest | `requirements.txt` |
| 8 | No Docker/CI needed | none exist |
| 9 | Env vars only | all config read and validated in `config.py`, `.env` never required, keys via `export` |
| 10 | Ready in seconds | no network at startup, no model loading, schema check is one PRAGMA |

## Features (§3)

- Two backend feature domains, both reading/writing SQLite: **Intel** and **Book**.
- Each must be something that could become its own microservice. The seam is `contracts.py`.

## Testing (§4)

- Unit tests with pytest on **core business logic**, not routing.
- **≥70% coverage** measured with pytest-cov.
- Coverage command and result go in `README.md`.

## Process deliverables (§5), 30% of the grade

### ADR.md
- Exactly **5** entries, in this exact format:
```
## [N]. <Title>
Date: YYYY-MM-DD
Status: Decided
Context: 1-3 sentences, what forced this decision
Decision: 1-2 sentences, what you chose
Alternatives considered: at least one real alternative, and why you rejected it
Consequences: 1-2 sentences, what this costs or enables later
```
- Required topics: (1) framework, (2) domain split, (3) SQLite schema decision, (4) testing approach, (5) one thing deliberately not built.
- Entries must span **at least 3 distinct commit dates**. Add each one on the day the decision is made.
- **Javi writes the decisions.** Agents only format and suggest alternatives.

### AI_USAGE.md
- One row per meaningful AI interaction.
- Columns: Date/commit | Tool | Prompt | Disposition (Accepted/Modified/Rejected) | What changed & why | In my own words, how this works
- The last column is the one that matters. Must use real function/variable names. **Javi writes it, never an agent.**

### Commits
- ≥12 commits, ≥6 distinct calendar days, no single day >40% of commits.
- Pushed to GitHub. They check **push** timestamps. Push every day.
- No "initial commit", "WIP", "update", "fix". Say what changed and why.
- No fabricated or backdated history.

## Comprehension check (§6), multiplies the whole grade

- 6 short questions, on paper, closed-book, about Javi's own repo, ADRs and AI log.
- Subtotal × check score. 88 × 0.60 = 52.8.
- Everything in this repo must be explainable by Javi without notes.

## Report (§8), not in the repo but built from it

- 4 to 5 pages: SDLC model + SMART goals, architecture diagram, DB diagram (must match ADR 3 and real schema), README, AI disclosure statement.
- Diagrams live in `docs/diagrams/` so they stay in sync with the code.

## Grading split

| Category | Weight |
|---|---|
| Working features (Intel 10%, Book 10%) | 20% |
| Testing (≥70% on core logic) | 15% |
| Code quality 10% + commit hygiene 10% | 20% |
| Docs: SDLC 5%, diagrams 5%, README 5% | 15% |
| ADR.md 15% + AI_USAGE.md 15% | 30% |
| **× Comprehension check** | **0-100%** |
