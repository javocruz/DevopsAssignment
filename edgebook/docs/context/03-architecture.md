# 03 - Architecture

## The pipeline

```
fetch markets -> gather news -> ask Jev -> decide bets -> settle bets -> score Jev
|--------------- Intel ----------------|  |------------- Book -------------|
                                  Estimate / Resolution
                                    (contracts.py)
```

## Folder structure (target, ~40 files)

```
edgebook/
  app.py               entrypoint: logging, init DB, build FastAPI app, mount routers, run uvicorn
  config.py            ALL env vars read + validated here, once, into a Settings object
  db.py                get_connection(), get_db() dependency, init_db() with schema versioning
  security.py          require_admin() dependency (optional ADMIN_TOKEN)
  contracts.py         Estimate and Resolution dataclasses. The seam.
  pipeline.py          the ONLY file allowed to import both intel and book
  requirements.txt     pinned versions
  intel/
    __init__.py
    sources.py         FixtureSource, PolymarketSource, parse_gamma_market(), get_source()
    news.py            FixtureNews, TheNewsApi, build_news_query(), filter_news_before(), get_news_source()
    decider.py         Decision, StubDecider, JevDecider, get_decider()
    estimates.py       build_state(), render_state(), run_estimates()
    repo.py            SQL for markets, price_snapshots, news_items, estimates
    routes.py          /markets..., /news..., /estimates...
  book/
    __init__.py
    strategy.py        compute_edge(), should_bet(), pick_side(), entry_price(), size_stake()   PURE
    settlement.py      settle_bet()                                                            PURE
    scoring.py         brier_score(), calibration_buckets()                                    PURE
    repo.py            SQL for bets
    routes.py          /portfolio
  templates/
    base.html
    dashboard.html     buttons call JSON routes with fetch(), no form library needed
  static/
    style.css
  fixtures/
    resolved_markets.json   markets + pre-resolution prices + outcomes + pre-snapshot headlines
  scripts/
    build_fixture.py   dev-only, run once by Javi with real keys to (re)build the fixture
  tests/
    conftest.py
    data/              saved sample API payloads (gamma, jev, thenewsapi)
    test_config.py  test_db.py  test_security.py
    test_sources.py  test_news.py  test_decider.py  test_estimates.py
    test_strategy.py  test_settlement.py  test_scoring.py  test_pipeline.py
  docs/
    context/           these files
    diagrams/          architecture.md, db-schema.md (Mermaid)
  AGENTS.md  CLAUDE.md  README.md  ADR.md  AI_USAGE.md  .gitignore
```

## The seam (the most important idea in this repo)

- `book/` **never** imports from `intel/`. `intel/` **never** imports from `book/`.
- Both import from `contracts.py`. Shared infra (`config`, `db`, `security`) is allowed in both.
- `pipeline.py` is the glue: it asks Intel for `Estimate` and `Resolution` objects and hands them to Book.
- Contracts hold **only plain types** (str, int, float). In Assignment 2 they become JSON with `dataclasses.asdict()` and `pipeline.py` becomes HTTP calls between two services. Neither domain's code changes.
- Book does not know Jev, Polymarket or TheNewsAPI exist.
- News lives **inside Intel**: it is "gathering context for an estimate", not its own business domain.
- The JSON API is the product. The dashboard is a thin page that only calls JSON routes.

## Who owns what

| Domain | Owns tables | Owns logic |
|---|---|---|
| Intel | `markets`, `price_snapshots`, `news_items`, `estimates` | fetching, parsing, news, building Jev state, calling the decider |
| Book | `bets` | edge, gating, sizing, settlement, scoring |

One SQLite file for now (the assignment wants one path). Book only ever queries `bets`, and no foreign key crosses the seam, so splitting into two DB files in A2 is a copy, not a redesign.

## Dependencies (allowed list, 6 packages, versions pinned)

| Package | Why |
|---|---|
| `fastapi` | web framework, request validation, auto docs at `/docs` |
| `uvicorn` | ASGI server, started from `app.py` so `python app.py` works |
| `jinja2` | server-rendered dashboard |
| `httpx` | HTTP client for Polymarket, TheNewsAPI, Jev. `MockTransport` makes tests offline |
| `pytest` | tests |
| `pytest-cov` | coverage |

- Pin exact versions (`fastapi==X.Y.Z`) from `pip freeze` after the first install. Reason: the A2 Docker build must get the same versions.
- Python **3.12** (documented in README).
- Standard library for everything else: `sqlite3`, `json`, `dataclasses`, `hashlib`, `os`, `pathlib`, `datetime`, `logging`, `re`.
- **Not used, on purpose:** ORM, pandas, numpy, `typesafe-sdk` (we call Jev with `httpx` so the request is visible and mockable), `python-dotenv` (a `.env` must never be required), `python-multipart` (dashboard uses `fetch()` + JSON), any retry or scheduler library.

## Environment variables (all read and validated in `config.py`)

| Var | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | port uvicorn binds on `0.0.0.0` |
| `DATA_DIR` | `./data` | folder for `edgebook.db`. The ONLY place the app writes. In A2, mount a volume here |
| `LOG_LEVEL` | `INFO` | stdout logging level |
| `ADMIN_TOKEN` | empty | if set, every POST route needs header `X-Admin-Token`. If empty, routes are open |
| `MARKET_SOURCE` | `fixture` | `fixture` or `polymarket` |
| `POLYMARKET_LIMIT` | `50` | markets pulled in polymarket mode |
| `NEWS_SOURCE` | `fixture` | `none`, `fixture` or `thenewsapi` |
| `THENEWSAPI_TOKEN` | empty | needed only for `NEWS_SOURCE=thenewsapi`. Missing -> warn, fall back to `fixture` |
| `NEWS_ARTICLES` | `3` | headlines per market (free plan gives 3 per request) |
| `NEWS_MAX_CALLS_PER_RUN` | `20` | hard cap on TheNewsAPI calls per request (free plan: 100/day) |
| `DECIDER` | `stub` | `stub` or `jev` |
| `TYPESAFE_API_KEY` | empty | needed only for `DECIDER=jev`. Missing -> warn, fall back to stub |
| `TYPESAFE_BASE_URL` | `https://api.typesafe.ai/v1/systemone` | Jev endpoint |
| `JEV_MODEL` | `jev-latest` | model name sent in the request |
| `HTTP_TIMEOUT` | `10` | seconds, every external call |
| `ESTIMATE_BATCH_LIMIT` | `20` | max markets per `/estimates/run` call, keeps requests short |
| `EDGE_THRESHOLD` | `0.08` | minimum absolute edge to bet |
| `MIN_CONFIDENCE` | `0.6` | minimum Jev confidence to bet |
| `MIN_INFO` | `0.4` | minimum info_score (0 to 1) to bet |
| `BASE_STAKE` | `10` | stake at exactly the threshold edge |
| `MAX_STAKE` | `50` | cap on any single bet |

Rules:
- No other file calls `os.environ`. Everything goes through `config.get_settings()`.
- **Fail fast** on invalid values (`EDGE_THRESHOLD=abc`, negative stakes, unknown `DECIDER`): raise a clear `ValueError` at startup naming the variable.
- **Missing optional keys never crash**: log a warning and fall back to the offline mode.
- Keys are set with `export` in the shell. Never in code, never committed, never logged.

## Routes

| Method + path | File | Admin? | Does |
|---|---|---|---|
| `GET /healthz` | `app.py` | no | `{"status": "ok", "schema_version": N}` |
| `POST /markets/sync` | `intel/routes.py` | yes | load markets from the active source, save markets + price snapshots |
| `GET /markets` | `intel/routes.py` | no | list markets |
| `POST /news/fetch` | `intel/routes.py` | yes | fetch + cache headlines for markets with none yet (respects `NEWS_MAX_CALLS_PER_RUN`) |
| `POST /estimates/run?context=news\|basic` | `intel/routes.py` | yes | run the decider on up to `ESTIMATE_BATCH_LIMIT` markets without an estimate at that context level |
| `GET /estimates` | `intel/routes.py` | no | list estimates (optional `?min_edge=`) |
| `POST /pipeline/auto-bet` | `pipeline.py` | yes | estimates -> Book -> paper bets |
| `POST /pipeline/settle` | `pipeline.py` | yes | resolutions -> Book -> settle open bets |
| `GET /scorecard?decider=&context=` | `pipeline.py` | no | Brier + calibration, never mixes deciders or context levels |
| `GET /portfolio` | `book/routes.py` | no | open + settled bets, total P&L |
| `GET /` | `pipeline.py` | no | dashboard page |

Batch routes return a summary: `{"processed": n, "skipped": n, "failed": [{"market_id", "reason"}]}`. One failing market never fails the whole run.

## Startup sequence (`python app.py`)

1. `logging.basicConfig(stream=sys.stdout, level=LOG_LEVEL)`, and `logging.getLogger("httpx").setLevel(logging.WARNING)` so request URLs (which contain `api_token`) are never logged.
2. `config.get_settings()` reads and validates env vars.
3. `db.init_db()` creates `DATA_DIR`, then checks the schema version (see `04-data-model.md`).
4. FastAPI app is built, routers mounted.
5. `uvicorn.run(app, host="0.0.0.0", port=settings.port)`.
No network calls at startup. Ready in ~1 second.

## Concurrency and SQLite

- Routes are plain `def` (not `async def`), `httpx` is used synchronously. Simpler to explain, enough at this scale.
- FastAPI runs `def` routes in a thread pool, and a `sqlite3` connection can't be shared across threads. So: **one connection per request** through the `get_db()` dependency (open, yield, close).
- `PRAGMA journal_mode=WAL` so a long write doesn't block reads. `PRAGMA foreign_keys=ON`.
- One uvicorn worker. SQLite + multiple workers is an A2 problem, noted, not solved now.

## External API behavior

- Every call has `timeout=HTTP_TIMEOUT`.
- No retry library. On timeout or HTTP error: log it (without the URL), record the market in `failed`, continue.
- TheNewsAPI results are cached in `news_items`. A market is never fetched twice.
- All three APIs are mocked in tests with `httpx.MockTransport` and saved payloads in `tests/data/`.
