# Edgebook

A paper-trading desk for prediction markets. Edgebook pulls markets, asks Jev (TypeSafe AI) for its own probability on each one, places paper bets where Jev disagrees with the crowd, and scores whether Jev was actually better than the market once markets resolve.

**Pipeline:** fetch markets -> gather news -> ask Jev -> decide bets -> settle bets -> score Jev

## Quick start

Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

With no env vars the app stays offline: fixture markets, fixture headlines, and the stub decider. Open http://localhost:8000. Leave the admin token box empty.

## Keys

Set keys in the shell. The app does not read a `.env` file. Do not commit them.

```bash
export TYPESAFE_API_KEY=your-key    # only for DECIDER=jev
export THENEWSAPI_TOKEN=your-token  # only for NEWS_SOURCE=thenewsapi
export ADMIN_TOKEN=your-token       # optional lock on POST routes
```

A missing `TYPESAFE_API_KEY` falls back to the stub. A missing `THENEWSAPI_TOKEN` falls back to fixture news. An empty `ADMIN_TOKEN` leaves POST routes open.

## Data

`DATA_DIR` is the only folder the app writes. The database file is `edgebook.db` inside it. Default is `./data`.

```bash
DATA_DIR=/tmp/edgebook python app.py
```

In Assignment 2, mount a volume at `DATA_DIR` so a container restart does not wipe the database.

## Configuration

Every variable is read in `config.py`. Invalid values raise `ValueError` and name the variable.

| Var | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | port uvicorn binds on `0.0.0.0` |
| `DATA_DIR` | `./data` | folder for `edgebook.db` |
| `LOG_LEVEL` | `INFO` | stdout logging level |
| `ADMIN_TOKEN` | empty | if set, every POST route needs header `X-Admin-Token` |
| `MARKET_SOURCE` | `fixture` | `fixture` or `polymarket` |
| `POLYMARKET_LIMIT` | `50` | markets pulled in polymarket mode |
| `NEWS_SOURCE` | `fixture` | `none`, `fixture`, or `thenewsapi` |
| `THENEWSAPI_TOKEN` | empty | needed only for `NEWS_SOURCE=thenewsapi` |
| `NEWS_ARTICLES` | `3` | headlines per market |
| `NEWS_MAX_CALLS_PER_RUN` | `20` | hard cap on TheNewsAPI calls per request |
| `DECIDER` | `stub` | `stub` or `jev` |
| `TYPESAFE_API_KEY` | empty | needed only for `DECIDER=jev` |
| `TYPESAFE_BASE_URL` | `https://api.typesafe.ai/v1/systemone` | Jev endpoint |
| `JEV_MODEL` | `jev-latest` | model name sent in the request |
| `HTTP_TIMEOUT` | `10` | seconds, every external call |
| `ESTIMATE_BATCH_LIMIT` | `20` | max markets per `/estimates/run` call |
| `EDGE_THRESHOLD` | `0.08` | minimum absolute edge to bet |
| `MIN_CONFIDENCE` | `0.6` | minimum Jev confidence to bet |
| `MIN_INFO` | `0.4` | minimum info_score (0 to 1) to bet |
| `BASE_STAKE` | `10` | stake at exactly the threshold edge |
| `MAX_STAKE` | `50` | cap on any single bet |

## Tests and coverage

```bash
pytest --cov=. --cov-report=term-missing
```

Total coverage: 97% (62 tests).

## Structure

- `app.py`: start the server, `/healthz`, static files
- `config.py`: env vars
- `db.py`: SQLite, schema version
- `security.py`: optional `ADMIN_TOKEN` on POST routes
- `contracts.py`: `Estimate` and `Resolution`, the only handoff
- `pipeline.py`: the only file that imports both `intel/` and `book/`, plus `GET /`
- `intel/`: markets, news, estimates
- `book/`: edge, settlement, scoring, bets
- `templates/` and `static/`: the dashboard. It only calls JSON routes. Charts are Chart.js 4.5.1, saved in `static/vendor/chart.min.js` and loaded from that file.
- `fixtures/resolved_markets.json`: offline markets
- `tests/`: offline tests, with saved API samples in `tests/data/`

Diagrams: [architecture](docs/diagrams/architecture.md) and [database schema](docs/diagrams/db-schema.md).

## Project docs

Graded docs stay at the project root. The spec is numbered, so read it in order.

- `README.md`: how to run the app
- `ADR.md`: the architecture decisions, written on the day each one is made
- `AI_USAGE.md`: one entry per AI interaction. The last field of each entry is written by hand
- `AGENTS.md`: instructions for coding agents. `CLAUDE.md` points here
- `docs/context/01-project.md`: pitch, users, scope
- `docs/context/02-assignment-rules.md`: hard constraints
- `docs/context/03-architecture.md`: files, env vars, routes
- `docs/context/04-data-model.md`: SQLite tables
- `docs/context/05-logic-spec.md`: strategy, settlement, scoring, Jev questions
- `docs/context/06-commit-plan.md`: what each commit contains
- `docs/context/07-learning-guide.md`: explain-back questions
