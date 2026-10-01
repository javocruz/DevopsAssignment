# AGENTS.md

Read this first. It is the entry point for any AI agent working on this repo.

## What this project is

**Edgebook**: a paper-trading desk for prediction markets.
Pipeline, always in this order:

**fetch markets -> gather news -> ask Jev -> decide bets -> settle bets -> score Jev**

- Domain A, **Intel** (`intel/`): fetch markets, gather news headlines, ask Jev for a probability, save Estimates.
- Domain B, **Book** (`book/`): read Estimates, decide paper bets, settle them, score Jev vs the market.
- The ONLY handoff between them: `Estimate` and `Resolution` records defined in `contracts.py`.

This is an individual university assignment (IE University, DevOps course, Assignment 1).
The student (Javi) will be quizzed on paper, closed-book, on every line of this code.
**Your job is to help him build it AND understand it.** Understanding is worth more than speed here.

## Where the details live

| File | Read it when |
|---|---|
| `docs/context/01-project.md` | You need the pitch, users, scope, what is out of scope |
| `docs/context/02-assignment-rules.md` | Before adding ANY file, dependency or tool. Hard constraints live here |
| `docs/context/03-architecture.md` | Before creating or moving files. Structure, env vars, routes, the seam |
| `docs/context/04-data-model.md` | Before touching SQL or tables |
| `docs/context/05-logic-spec.md` | Before writing strategy, settlement, scoring, or Jev questions |
| `docs/context/06-commit-plan.md` | To find out what the current commit should contain. Work ONE commit at a time |
| `docs/context/07-learning-guide.md` | After each commit, to run the explain-back |

## Decisions belong to Javi

Stop and ask before choosing. If more than one reasonable option exists, name the options in plain language and wait. Do not pick for him.

This includes what to build next, commit wording, history rewrites, new dependencies, ADR Decision and Alternatives, and any behavior the spec does not already fix.

If the spec already decides it, follow that and say which part you followed.

## Opus commits

Opus is cancelled. C8 and C9 were done in Claude Code. **C13** and **C18** are done in this chat, same as the other commits.

## Hard rules for agents

1. **One commit at a time.** Find the next unchecked commit in `06-commit-plan.md`. Only touch the files it lists. Stop when its "Done when" is met. Commit message starts with the plan id: `C1: Add validated config reading all env vars with offline defaults`.
2. **Never** create a Dockerfile, docker-compose, `.github/workflows/`, Terraform/Bicep/ARM, or anything requiring a `.env` file to exist.
3. **Never** add a dependency not listed in `03-architecture.md` without asking Javi first. Soft cap is 12 third-party packages.
4. **Never** use an ORM. Plain `sqlite3` from the standard library, written SQL. (Learnability decision.)
5. **Never** write the Decision or Alternatives of an ADR on your own. Javi decides. You may format what he tells you and suggest alternatives he should consider.
6. **Never** fake, backdate or batch git history. Javi commits and pushes himself, on the day planned.
7. **Never** call the real Jev, Polymarket or TheNewsAPI in tests. Mock them with `httpx.MockTransport` and saved payloads in `tests/data/`.
8. Keep math in **pure functions** (numbers in, numbers out, no DB, no HTTP). Keep I/O in separate files.
9. Use plain names that match the docs exactly (`compute_edge`, `should_bet`, `size_stake`, `settle_bet`, `brier_score`, `calibration_buckets`). Javi memorizes these names.
10. Short functions. Comments explain **why**, not what. No clever one-liners.
11. Do not invent Jev or Polymarket API details. The verified Jev format is in `05-logic-spec.md`. If unsure about anything else, say so and point Javi to the docs (`docs.typesafe.ai`, `docs.polymarket.com`).
12. **API keys** (`TYPESAFE_API_KEY`, `THENEWSAPI_TOKEN`, `ADMIN_TOKEN`) come only from env vars via `config.py`. Never hardcode, print, log, commit, or put them in `state_json`, sample payloads, or error messages. TheNewsAPI's token is in the URL, so never log request URLs.
13. Every external call has a timeout. One failing market is logged and skipped, never crashes a batch.
14. The only place the app writes files is `DATA_DIR`.

## After every change, you must give Javi

1. **Explain-back**: 3 to 6 bullets on how the new code works, using the real function and variable names, in plain language.
2. **A worked example** if any math was added (real numbers, step by step).
3. **Write the `AI_USAGE.md` entry into the file as a new table row** with the six required columns. Fill Date/commit, Tool, Prompt, Disposition, and What changed. Leave **In my own words, how this works** blank. Never write that cell for him. Do not switch the log to headings. Do not only paste the entry in chat.
4. **2 or 3 quiz questions** from `07-learning-guide.md` that the commit touches.

## Tone

Javi prefers direct, informal, plain-language explanations. Bullets over paragraphs. No em dashes.

After every AI_USAGE draft, also give an easy explanation of that draft, in plain language, so he can rewrite it in his own words.
