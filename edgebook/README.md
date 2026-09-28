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

- `ADR.md`: architecture decision log
- `AI_USAGE.md`: AI usage log
- `docs/context/`: project spec
- `docs/diagrams/`: architecture and DB diagrams
