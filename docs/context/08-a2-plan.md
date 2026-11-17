# 08 - Assignment 2 plan (split, ship, operate)

Agents: read this before any A2 work. It overrides `02-assignment-rules.md` and `06-commit-plan.md` where they conflict.
One commit at a time. Tick a box only after Javi has committed, pushed, and merged the PR.
Javi writes every ADR decision and every "In my own words" cell in `AI_USAGE.md`. Agents only format.
Deadline: **2026-11-22**. The six commit days are 17, 18, 19, 20, 21, and 22. Skipping a day fails the six-day rule.

## What A2 changes (hard rules)

- **Exactly 2 service containers**: `intel` and `book`, each in `services/<name>/` with its own Dockerfile, pinned `requirements.txt`, `migrations/`, `openapi.yaml`, and tests.
- **Static UI** in `ui/`. No server-rendered templates. Service URLs come from `ui/config.js`, written at deploy time. The polished dashboard already on `main` (`templates/`, `static/app.js`) is the source to move, not a new product.
- **Database per service**: SQL Server. Locally one `mcr.microsoft.com/mssql/server:2022-latest` container with two databases (`intel`, `book`) created by idempotent `db/init.sql`. On Azure, two serverless databases on one server. Each service has its own login, reads `DATABASE_URL`, and never touches the other database.
- **HTTP between services**: Book finds Intel via `INTEL_URL`. Nothing hardcoded.
- **Dockerfiles**: no `COPY . .`, no secrets or `.env` in the image, pinned deps, non-root user.
- **`docker-compose.yml`** at the root: `docker compose up --build` from a clean clone. UI served by `nginx:alpine` with `ui/` mounted. nginx is not a service container.
- **CI/CD** in `.github/workflows/`. CI on every push and PR. CD on `main` only.
- **Migrations**: numbered SQL files, applied in order on startup, recorded in `schema_migrations`, each runs once, never edited after applied, never drop tables.
- **`GET /health`** replaces `/healthz`: `200 {"status":"ok","db":"ok","version":"<git sha>"}` when the service can read and write its own database, else `503`. It never checks the other service.
- **Logs**: one stdout line per request: method, path, status, duration, request id.
- **CORS in FastAPI** (`CORSMiddleware`), origins from `CORS_ORIGINS` (local value includes `http://localhost:8080`), allow `Content-Type`, `X-Admin-Token`, and `X-Request-ID`. Never the Container Apps ingress CORS setting.
- **No secrets in the repo**, including compose and history. A leaked secret is rotated within 24 h and noted in the README. An unreported leak caps the grade at 40.
- **Same stack**: Python 3.12, FastAPI, no ORM. Soft cap about 12 third-party packages per service.
- **Changes reach `main` through pull requests.**
- **Out of scope**: a third container, Redis, queues, schedulers, any other database, always-on compute, accounts, uploading strategies, new deciders.

## Architecture after the split

```
browser -> ui (storage static website)
            |-- GET/POST --> intel  (markets, price_snapshots, news_items, estimates)
            |-- GET/POST --> book   (bets, intel_cache)
book --HTTP--> intel   GET /estimates, GET /resolutions, GET /estimates/{id}
```

Intel never calls Book. `pipeline.py` is deleted. Its routes move into Book. `book/intel_client.py` does the HTTP. Book does not import the Intel package. A grep for `from intel` or `import intel` under `services/book/` must be empty. The word `intel` will still appear in `INTEL_URL` and `intel_client.py`.

`contracts.py` (`Estimate`, `Resolution`) is copied into Book as the shape it parses from JSON. It must match Intel's `openapi.yaml`.

`bets.estimate_id` stays a plain id. There is no foreign key across the seam. Book checks the estimate by calling Intel.

New Intel reads, exposing data it already stores:

- `GET /resolutions` returns `Resolution` records as JSON.
- `GET /estimates/{id}` returns one estimate including `state_json`. `outcome` and `yes_price` are never in that document.

Story, in the README and the UI labels only: Edgebook is a lab for testing forecasters and strategies. Jev is the first forecaster. Do not build accounts or uploads. That is ADR 10.

## Failure design (three separate rules)

1. **Service to its own database.** Retry with exponential backoff for up to about 90 seconds. Azure can take about 60 seconds to resume a paused database (error 40613 or a timeout). This applies at startup, while migrations run, and on each connection.
2. **Book to Intel.** `INTEL_TIMEOUT_S` defaults to 10, plus one retry. Then:
   - Scorecard: if Book has a cached Intel response in `intel_cache` (`key`, `payload`, `fetched_at`), return it with `stale: true` and `fetched_at`. The UI says the data is old.
   - Auto-bet and settle: `503` with `{"error":"intel_unavailable","detail":"Intel is starting up or down, try again in a minute"}`. Never place or settle a bet from stale estimates.
   - Portfolio: always served from Book's own `bets` table.
3. **UI.** On 503 or a network error, show "Waking up the lab..." and retry a few times. Never a blank page.

## SQLite to SQL Server

Driver is `pymssql`, so the image does not need an ODBC driver. **Before C5**, test one encrypted connection to the Azure SQL server. If it fails, switch this plan to `pyodbc` with `Encrypt=yes` before any T-SQL is written. Do not leave that check until deploy day.

| SQLite | SQL Server |
|---|---|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `INT IDENTITY(1,1) PRIMARY KEY` |
| `TEXT` | `NVARCHAR(n)` (`NVARCHAR(MAX)` for `state_json` and cache payloads) |
| `REAL` | `FLOAT` |
| `INSERT OR IGNORE` | `INSERT ... SELECT ... WHERE NOT EXISTS (...)`, keep UNIQUE, catch errors 2627 and 2601 |
| `LIMIT n` | `SELECT TOP (n)` or `OFFSET ... FETCH` |
| `PRAGMA user_version` | `schema_migrations` |
| `?` placeholders | `%s` for pymssql |

Dates stay ISO strings in `NVARCHAR(32)` so `filter_news_before` can keep comparing strings. `DATABASE_URL` is parsed in each service's `config.py`.

## Migrations

Runner: `services/<name>/migrate.py`. It creates `schema_migrations(version, applied_at)` if missing, applies unapplied files in order, each in a transaction, and logs the name. A second boot applies nothing.

- `001_init.sql` creates the tables. Intel: `markets`, `price_snapshots`, `news_items`, `estimates`. Book: `bets`, `intel_cache`.
- **002, data-preserving, Book only:** `ALTER TABLE bets ADD strategy NVARCHAR(32) NOT NULL CONSTRAINT df_bets_strategy DEFAULT 'edge_v1'`. Existing rows become `edge_v1`, which is true because only one betting rule has ever existed.

Azure evidence order: deploy with only 001, run sync, estimates, auto-bet, and settle, record the rows, then deploy 002 and show the same rows with `strategy = edge_v1` plus the startup log line.

## Local passwords

Until the professor says a throwaway password in the compose file is acceptable, compose reads `MSSQL_SA_PASSWORD`, `INTEL_DB_PASSWORD`, and `BOOK_DB_PASSWORD` from the environment. Commit `.env.example` with placeholders only. The real `.env` is gitignored. README step: `cp .env.example .env` before `docker compose up --build`. `db/init.sql` uses sqlcmd variables, never literal passwords.

Apple Silicon: enable Rosetta for the SQL Server image. Ports: intel `8001:8000`, book `8002:8000`, ui `8080:80`. Inside compose, `INTEL_URL=http://intel:8000`.

## Testing

- Per service, from that service's directory: `pytest --cov=. --cov-fail-under=70`.
- Pure functions stay free of the database: `compute_edge`, `should_bet`, `size_stake`, `settle_bet`, `brier_score`, `calibration_buckets`, `build_state`, `filter_news_before`, `parse_jev_response`.
- Repo and migration tests use SQL Server. Locally that is compose. In CI it is a service container. CI never connects to Azure SQL.
- Cross-seam test: `httpx.MockTransport` stands in for Intel. Auto-bet with a normal payload places a bet. Intel down returns the 503 body. Scorecard with a cache row returns `stale: true`. Portfolio stays 200.
- Dev dependencies live in `requirements-dev.txt` (pytest, pytest-cov, ruff). Images install only `requirements.txt`.

## UI (one commit, not a new app)

`ui/index.html`, `ui/app.js`, `ui/style.css`, `ui/config.js`, and the vendored Chart.js already in the repo. Move the current dashboard behavior off Jinja. The page calls both services. It shows the lab summary, forecaster vs market, markets, portfolio, and each service's `/health`. It shows the stale banner and the waking-up banner. The admin token stays in `sessionStorage`. Drop `jinja2` from the service requirements when the templates are removed.

## What this schedule dropped

These were in the nine-day plan and are not separate commits. Do not add them back unless a day finishes early: five-file design system, compose smoke in CI, gitleaks, pip-audit, branch protection, a rollback workflow, a separate runbook commit. The recovery plan is written in ADR 7 (new forward migration, redeploy an older image by hand if needed, Azure point-in-time restore). Diagrams land in the last commit. The report still needs them.

## Commit plan

16 commits, 6 days, at most 3 on days 1 to 5 and 4 on day 6. Four of 16 is 25 percent, under the 40 percent cap. Each day: branch off `main`, commit, push, open a PR, merge.

### Day 1 (Tue 17 Nov) branch `a2-plan`

- [x] **C1** `Update agent rules for A2 and add the split plan`
- [x] **C2** `Add ADR 6: split Edgebook along the Intel/Book seam` (dated 2026-11-17). Javi writes it.
- Not a commit: activate Azure for Students and write down the five allowed regions.

### Day 2 (Wed 18 Nov) branch `a2-services`

- [ ] **C3** `Split the monolith into intel and book services along the ADR 2 seam`
  - Move code into `services/intel/` and `services/book/`. Still SQLite, so tests stay green.
  - Book gets auto-bet, settle, and the scorecard, plus `intel_client.py`.
  - Intel gets `GET /resolutions`. Delete `pipeline.py`. Fixtures move with Intel.
- [ ] **C4** `Add /health, request logging, CORS, and the estimate audit route`
  - `/health` checks its own database. `version` comes from `GIT_SHA` (default `dev`).
  - One log line per request, and `intel_client.py` forwards `X-Request-ID`.
  - `CORSMiddleware` from `CORS_ORIGINS`.
  - `GET /estimates/{id}` returns `state_json`. Test that `outcome` and `yes_price` are absent.

### Day 3 (Thu 19 Nov) branch `a2-sqlserver`

- [ ] **C5** `Port Intel to SQL Server with a numbered migration runner`
- [ ] **C6** `Port Book to SQL Server with bets and intel_cache`
- [ ] **C7** `Add ADR 7 on data per service and migrations` (dated 2026-11-19). Javi writes: two databases, no foreign key across the seam, `intel_cache` is a copy not a join, recovery is a new migration plus point-in-time restore.

### Day 4 (Fri 20 Nov) branch `a2-containers`

- [ ] **C8** `Add Dockerfiles, compose, and db init for the two-service stack`
  - Done when a clean clone, after `cp .env.example .env`, runs `docker compose up --build` and both `/health` routes return 200. nginx can serve a placeholder page.
- [ ] **C9** `Add cached degraded responses and the cross-seam tests`
  - Not a commit, but do it this day if Azure is active: create the resource group and the SQL server, then run the pymssql encryption check if C5 has not already proved it.

### Day 5 (Sat 21 Nov) branch `a2-ui-ci`

- [ ] **C10** `Move the dashboard to a static UI that calls both services`
- [ ] **C11** `Add OpenAPI documents per service and system.yaml`
  - Needs `system.schema.json` from Blackboard. Every env var is listed. Secrets have no default and are marked `secret: true`.
- [ ] **C12** `Add CI and ADR 9 on the pipeline and testing` (ADR dated 2026-11-21). Javi writes the ADR before the commit: what CI gates, the stub seam test, and what is not tested (live Jev, Polymarket, TheNewsAPI).

### Day 6 (Sun 22 Nov) branch `a2-deploy`

Azure setup must already be done before C14. Document the commands you actually ran.

- [ ] **C13** `Document local run and the Azure setup in the README`
- [ ] **C14** `Add CD to Azure: SHA-tagged images, Container Apps, static UI, and a health gate`
  - `cd.yml` on push to `main` calls `ci.yml`, then deploys with `id-token: write`. Images are `ghcr.io/<owner>/<image>:$GITHUB_SHA` with `provenance: false`. Container Apps get the image, `GIT_SHA`, and secrets via `secretref`. Write `ui/config.js`, upload `ui/` to `$web`, retry `/health` for about 5 minutes.
  - Keep the link to the first failed run.
- [ ] **C15** `Add migration 002: record the betting strategy on every bet`
  - Before this commit: run sync, estimates, auto-bet, and settle on Azure, and save a screenshot of the rows.
- [ ] **C16** `Add ADR 8, ADR 10, the diagrams, and the live URL` (both ADRs dated 2026-11-22). Then `git tag submission <sha>` and `git push origin submission`.

ADR 8 is the serverless cost model, scale to zero, database pause, connection retries, one replica so migrations cannot run twice, and what would change at 100x traffic. ADR 10 is public forecaster submissions, which we do not build: they need accounts, a sandbox, and abuse limits, and they are worth building only when more than one trusted person needs to add a forecaster.

## Final checklist

- [ ] Clean clone, `cp .env.example .env`, `docker compose up --build`
- [ ] CI green on the tagged commit, coverage at least 70 percent per service
- [ ] Live URL loads, cold start shows the waking-up banner
- [ ] `docker compose stop intel`: portfolio works, scorecard is stale, auto-bet returns the 503
- [ ] No keys in the tree or history
- [ ] ADR 6 to 10 exist on at least 3 dates. ADR 1 to 5 stay as they are
- [ ] At least 12 new commits, 6 days, no day over 40 percent, all via PRs
- [ ] Professors have Reader on `rg-<prefix>`
- [ ] Report: before and after architecture, deployment diagram, one database diagram per service, migration evidence, partial-failure evidence, one green CD run and one failed-then-fixed run, README, AI disclosure
