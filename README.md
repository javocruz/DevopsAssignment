# Edgebook

A paper-trading desk for prediction markets. Edgebook pulls markets, asks Jev (TypeSafe AI) for its own probability on each one, places paper bets where Jev disagrees with the crowd, and scores whether Jev was actually better than the market once markets resolve.

**Pipeline:** fetch markets -> ask Jev -> decide bets -> settle bets -> score Jev

> Status: in progress. Setup, env vars and coverage sections get completed as the app is built (see `docs/context/06-commit-plan.md`).

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Runs offline by default (bundled fixture markets + stub decider). Open http://localhost:8000.

## Configuration

TODO: env var table (C16)

## Tests and coverage

TODO: command and result (C14)

## Project docs

Graded docs stay at the project root. The spec is numbered, so read it in order.

- `README.md`: how to run the app
- `ADR.md`: the five architecture decisions, written on the day each one is made
- `AI_USAGE.md`: one entry per AI interaction. The last field of each entry is written by hand
- `AGENTS.md`: instructions for coding agents. `CLAUDE.md` points here
- `docs/context/01-project.md`: pitch, users, scope
- `docs/context/02-assignment-rules.md`: hard constraints
- `docs/context/03-architecture.md`: files, env vars, routes
- `docs/context/04-data-model.md`: SQLite tables
- `docs/context/05-logic-spec.md`: strategy, settlement, scoring, Jev questions
- `docs/context/06-commit-plan.md`: what each commit contains
- `docs/context/07-learning-guide.md`: explain-back questions
- `docs/diagrams/`: architecture and database diagrams, added with later commits
