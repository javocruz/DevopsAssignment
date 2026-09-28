# 06 - Commit plan

22 commits over 7 days. Max 4 on any day (18%, cap is 40%).
**One commit at a time. Tick the box only after Javi has committed AND pushed.**

For EVERY commit, Javi also:
- adds the AI_USAGE.md row(s), last column in his own words
- runs `pytest` before committing (once tests exist)
- pushes the same day (`git push`), they check push timestamps

Message rule: prefix the plan id, then say what changed and why. Example: `C1: Add validated config reading all env vars with offline defaults`. Never "fix", "update", "WIP", "initial commit".
Keys: `export TYPESAFE_API_KEY=...` and `export THENEWSAPI_TOKEN=...` in the shell. Never in files.

---

## Mon Sep 28

### [x] C0. `Add project context docs and agent instructions for Edgebook`
- **Files:** `AGENTS.md`, `CLAUDE.md`, `docs/context/01..07`, `README.md`, `ADR.md`, `AI_USAGE.md`, `.gitignore`
- **Tasks:** `git init`, GitHub repo, push.
- **AI_USAGE row:** docs drafted with Claude.

### [x] C1. `Add validated config reading all env vars with offline defaults`
- **Files:** `config.py`, `requirements.txt`, `tests/test_config.py`
- **Tasks:**
  - `Settings` frozen dataclass with every var in `03-architecture.md`, typed.
  - `get_settings()` reads `os.environ`. Invalid values raise `ValueError` naming the var. Enum vars (`MARKET_SOURCE`, `NEWS_SOURCE`, `DECIDER`) checked against allowed values.
  - venv on Python 3.12, `pip install fastapi uvicorn jinja2 httpx pytest pytest-cov`, then pin the 6 exact versions from `pip freeze` in `requirements.txt`.
- **Tests:** defaults with empty env; `PORT=9000` -> int 9000; `EDGE_THRESHOLD=abc` -> ValueError; `DECIDER=banana` -> ValueError.
- **Done when:** tests pass.

### [ ] C2. `Add FastAPI entrypoint, per-request SQLite connections and versioned schema`
- **Files:** `app.py`, `db.py`, `tests/test_db.py`, `tests/conftest.py`
- **Tasks:**
  - `db.get_connection()`: `row_factory = sqlite3.Row`, `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL`.
  - `db.get_db()`: FastAPI dependency, opens a connection, yields, closes.
  - `db.init_db()`: create `DATA_DIR`, schema versioning with `PRAGMA user_version` exactly as in `04-data-model.md`, all 5 tables.
  - `app.py`: stdout logging, `httpx` logger to WARNING, `init_db()`, `GET /healthz` with schema version, `uvicorn.run(app, host="0.0.0.0", port=settings.port)`.
  - `conftest.py`: `tmp_db` fixture (sets `DATA_DIR` to `tmp_path`, runs `init_db()`).
- **Tests:** fresh DB gets version 1 + 5 tables; second `init_db()` is a no-op; wrong version raises RuntimeError.
- **Done when:** `python app.py` starts in ~1 s, `/healthz` ok, `sqlite3 data/edgebook.db ".tables"` shows 5 tables.

### [ ] C3. `Add ADR 1: choose FastAPI over Flask and Django`
- **Files:** `ADR.md`. Javi writes it. Dated 2026-09-28.

---

## Tue Sep 29

### [ ] C4. `Add Estimate and Resolution contracts and ADR 2 on the Intel/Book seam`
- **Files:** `contracts.py`, `intel/__init__.py`, `book/__init__.py`, `ADR.md`
- **Tasks:** dataclasses exactly as `05-logic-spec.md`. Javi writes ADR 2 (mention: news inside Intel, one DB file now, per-domain DBs in A2).
- **Done when:** imports work, ADR 2 dated 2026-09-29.

### [ ] C5. `Add fixture market source and Intel repo for markets and snapshots`
- **Files:** `intel/sources.py` (FixtureSource), `intel/repo.py`, `fixtures/resolved_markets.json` (markets only for now, 5 hand-made rows are fine until C8 rebuilds it), `tests/test_sources.py`
- **Tasks:** `INSERT OR IGNORE` for markets and snapshots; `list_markets`, `latest_snapshot`.
- **Tests:** fixture rows have required keys, `0 < yes_price < 1`, outcome in {0,1}; saving twice doesn't duplicate.

### [ ] C6. `Add Polymarket source parsing Gamma markets and JSON-encoded outcomePrices`
- **Files:** `intel/sources.py` (PolymarketSource, `parse_gamma_market`, `get_source`), `intel/routes.py` (`POST /markets/sync`, `GET /markets`), `app.py` (mount), `tests/data/gamma_sample.json`, `tests/test_sources.py`
- **Tasks:** verify Gamma params in docs.polymarket.com first. Save one real response as the sample.
- **Tests:** parse sample; non-binary -> None; fetch with `httpx.MockTransport`; timeout -> error summary, no crash.

---

## Wed Sep 30

### [ ] C7. `Add stub and Jev deciders with parsing of Jev choice and score answers`
- **Files:** `intel/decider.py`, `tests/data/jev_sample.json`, `tests/test_decider.py`
- **Tasks:** request exactly as `05-logic-spec.md`. Make ONE real call with your key from a Python shell, save the response as `jev_sample.json` (remove anything sensitive).
- **Tests:** stub deterministic + in range; `parse_jev_response(sample)` -> correct Decision; score 3.0 -> 0.75; missing key -> stub; JevDecider via MockTransport sends `Authorization: Bearer` and all 3 questions.

### [ ] C8. `Add TheNewsAPI source with headline cache and look-ahead filter`
- **Files:** `intel/news.py`, `intel/repo.py` (news queries), `intel/routes.py` (`POST /news/fetch`), `scripts/build_fixture.py`, `fixtures/resolved_markets.json` (rebuilt, headlines stored as title + description + url + date only), `tests/data/thenewsapi_sample.json`, `tests/test_news.py`
- **Tasks:**
  - `build_news_query`, `filter_news_before`, FixtureNews, TheNewsApi, `get_news_source`, `fetch_news_for_markets` with call cap.
  - `scripts/build_fixture.py`: pulls 30 to 40 resolved binary Polymarket markets, a pre-resolution price, and 3 headlines each with `published_before=captured_at`. Hand-edit `news_query` where the auto one is bad. Uses ~40 of your 100 daily news calls, run it once.
- **Tests:** query builder example; filter drops future items and sorts newest first; TheNewsApi via MockTransport never puts the token in any logged message; cap stops at N calls; cached market isn't fetched again.

### [ ] C9. `Add estimate runs that store the exact state sent to the decider`
- **Files:** `intel/estimates.py`, `intel/repo.py` (estimates + `list_estimate_records`, `list_resolutions`), `intel/routes.py` (`POST /estimates/run`, `GET /estimates`), `tests/test_estimates.py`
- **Tasks:** `days_to_resolution`, `build_state`, `render_state`, `run_estimates` with batch limit and per-market failure handling.
- **Tests:** state never has `outcome`/`yes_price`; `basic` has no headlines, `news` does; running twice is a no-op; one failing market doesn't stop the batch; `list_estimate_records` returns `Estimate` objects.

### [ ] C10. `Add ADR 3 on the SQLite schema and the DB diagram`
- **Files:** `ADR.md`, `docs/diagrams/db-schema.md`. Javi picks one option from `04-data-model.md`. Dated 2026-09-30 (3rd distinct ADR date).

---

## Thu Oct 1

### [ ] C11. `Add edge, bet gating and stake sizing to book strategy`
- **Files:** `book/strategy.py`, `tests/test_strategy.py`
- **Tests:** all worked examples, exact threshold, negative edge. File imports nothing from `intel`, `db`, `httpx`.

### [ ] C12. `Add settlement with P&L for Yes and No bets`
- **Files:** `book/settlement.py`, `tests/test_settlement.py`

### [ ] C13. `Add bets repo and pipeline routes for auto-betting and settling`
- **Files:** `book/repo.py`, `book/routes.py` (`GET /portfolio`), `pipeline.py`, `app.py` (mount), `tests/test_pipeline.py`
- **Tests:** full offline run on `tmp_db`: sync -> news -> estimate -> auto-bet -> settle, every bet has status + pnl; auto-bet twice doesn't double bet; `grep -r "from intel" book/` empty.

---

## Fri Oct 2

### [ ] C14. `Add Brier score and calibration comparing Jev and market per context level`
- **Files:** `book/scoring.py`, `pipeline.py` (`GET /scorecard`), `tests/test_scoring.py`
- **Tests:** Brier example, empty -> None, p = 1.0 last bucket, scorecard never mixes deciders or context levels.

### [ ] C15. `Add ADR 4 on testing focus and record coverage in README`
- **Files:** `ADR.md`, `README.md`, tests to close gaps
- `pytest --cov=. --cov-report=term-missing` ≥70%, pasted in README.

### [ ] C16. `Run real Jev on fixture markets with and without news`
- **Files:** `docs/results.md` (the scorecard numbers + 3 lines of interpretation)
- **Tasks:** with your keys set, `DECIDER=jev`, run estimates `?context=basic` and `?context=news`, auto-bet, settle, copy both scorecards. This is the headline result for the report.
- Note: needs ~80 Jev calls, well within cost.

---

## Sat Oct 3

### [ ] C17. `Protect POST routes with an optional admin token`
- **Files:** `security.py`, route files, `tests/test_security.py`
- **Tests:** no `ADMIN_TOKEN` -> open; set + right header -> 200; set + wrong/missing -> 401; `/healthz` always open.

### [ ] C18. `Add dashboard showing Jev vs market, portfolio and scorecard`
- **Files:** `templates/base.html`, `templates/dashboard.html`, `static/style.css`, `pipeline.py` (`GET /`)
- Buttons use `fetch()` to call JSON routes (sends `X-Admin-Token` from an input box if set). Scorecard has a decider + context selector.

### [ ] C19. `Add architecture diagram and full README setup instructions`
- **Files:** `docs/diagrams/architecture.md`, `README.md` (Python 3.12, setup, run, env var table, keys via export, DATA_DIR as the volume path, tests + coverage, structure)

### [ ] C20. `Add ADR 5: <Javi's pick: paper trading only / no user accounts / no scheduler>`
- **Files:** `ADR.md`. Dated 2026-10-03.

Also today (not in repo): draft the report.

---

## Sun Oct 4 (deadline 23:59, aim to finish by 20:00)

### [ ] C21. `<name the real issues found in the fresh-clone check>`
Final checklist:
- [ ] Fresh clone -> venv -> `pip install -r requirements.txt` -> `python app.py` works with ZERO env vars and no internet
- [ ] `PORT=9000 DATA_DIR=/tmp/eb python app.py` works
- [ ] Grep the repo and logs for your keys: nothing (`git grep -n "<first 6 chars of key>"`)
- [ ] No Dockerfile, compose, workflows, IaC
- [ ] Coverage ≥70% in README
- [ ] 5 ADRs, 3+ distinct dates
- [ ] AI_USAGE.md complete, last column yours on every row
- [ ] ≥12 commits, ≥6 days, no day >40%, all pushed
- [ ] Diagrams match the code
- [ ] Report submitted
