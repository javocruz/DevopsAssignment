# 01 - Project

## One-line pitch

Edgebook pulls prediction markets, asks Jev (TypeSafe AI's System One model) for its own probability on each one, flags where Jev disagrees with the crowd, places **paper** bets, and measures whether Jev's "edge" was real once markets resolve.

## Background, in plain terms

- A prediction market asks a yes/no question ("Will X happen by Dec 31?").
- The price of "Yes" is between 0 and 1 and **is** the crowd's probability. 0.65 = 65% likely.
- Jev returns typed answers with probabilities. We ask it the same yes/no question and get its own probability.
- **Edge** = Jev's probability minus the market's price. If Jev says 0.75 and the market says 0.60, Jev thinks Yes is underpriced.

## Stakeholder and users (invented, for justifying decisions)

- **Stakeholder:** a student investing club (~40 analysts) that wants to test whether AI-assisted forecasting beats the crowd before anyone risks real money.
- **Users:** club analysts who open a dashboard, see Jev vs market side by side, see the paper portfolio and the scorecard.
- **What they care about:** an audit trail of every call, honest scoring, zero real money at risk.
- **Scale assumption:** a few hundred markets and a few thousand estimates per semester. SQLite handles this easily.

## In scope

- Two data sources for markets: a bundled **fixture** of already-resolved markets (default) and the live **Polymarket Gamma API** (optional).
- Two deciders: a deterministic **stub** (default) and the real **Jev** API (optional, needs a key).
- News context: bundled **fixture** headlines (default) and live **TheNewsAPI** (optional, needs a token), cached in SQLite. Estimates run at two context levels, `basic` and `news`, scored separately.
- Optional `ADMIN_TOKEN` protecting POST routes.
- Estimates, paper bets, settlement, P&L, Brier score, calibration buckets.
- A simple server-rendered dashboard.

## Out of scope (do not build)

- Real trading, wallets, or Polymarket CLOB order placement (future ADR 5).
- User accounts / login (a single shared admin token instead).
- Background schedulers, cron, Celery, Redis, queues.
- A vector DB, ORM, or any external database.
- Real public deployment (that is Assignment 2).

## Honest caveats (these go in the report)

- Jev only knows what is in the state we send it. With no news attached, it is mostly guessing. That is why we record `info_score` and compare `basic` vs `news` runs.
- News rejected alternatives: NewsAPI.org (free plan is dev-only and 1 month history), Massive (stock-ticker news only).
- Stretch ideas, only if time: category base rate in the state, a status-quo Noul question.
- Markets already price in public info, so real edge will probably be small. The scorecard is the point.
- **Look-ahead bias:** in fixture mode, Jev must only see information that existed at the snapshot time. The fixture stores a pre-resolution price, headlines are cut off at the snapshot time by `filter_news_before()`, and the outcome never reaches the decider.
