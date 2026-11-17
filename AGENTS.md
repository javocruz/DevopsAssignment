# AGENTS.md

Read this first. It is the entry point for any AI agent working on this repo.

## What this project is

**Edgebook**: a lab for testing prediction-market forecasters and strategies with paper money. Jev is the first forecaster.

- **Intel** (`services/intel/`): markets, prices, news, forecasts (estimates).
- **Book** (`services/book/`): paper bets, settlement, scoring. Calls Intel over HTTP for estimates and resolutions.
- **UI** (`ui/`): static site calling both services.

This is IE University DevOps, **Assignment 2**: split, containerize, migrate, CI/CD, deploy to Azure.
Javi is quizzed on paper, closed-book, on every line, including Dockerfiles and workflows.
**Your job: help him build the best version of this AND understand it.**

## Where the details live

| File | Read it when |
|---|---|
| `docs/context/08-a2-plan.md` | Always first. A2 rules, architecture, UI spec, commit plan |
| `docs/context/05-logic-spec.md` | Before touching strategy, settlement, scoring, deciders |
| `docs/context/04-data-model.md` | Before touching tables (now T-SQL, see 08) |
| `docs/context/07-learning-guide.md` | For explain-back questions |
| `docs/context/01-03, 06` | A1 history. Where they conflict with 08, 08 wins |

## Hard rules (graded or safety, never break)

1. **No secrets anywhere in the repo**: source, compose, workflows, tests, fixtures, logs, history. Never read `.env`. Never ask Javi to paste a key in chat.
2. **Never write the Decision or Alternatives of an ADR**, and never fill the "In my own words" column of AI_USAGE.md. Javi writes both. You may format and suggest alternatives.
3. **Never fake, backdate or batch git history.** Javi commits and pushes himself, through PRs.
4. **Never create, change or delete Azure resources yourself.** Write the `az` commands for the README; Javi runs them. After setup, only the pipeline changes Azure.
5. **Migrations**: never edit an applied migration, never drop or recreate tables on boot. Fixes go in a new numbered file.
6. **Tests never call real external services** (Jev, Polymarket, TheNewsAPI, Azure SQL). Mock them or use the local SQL Server container.
7. **Stay inside the A2 brief**: exactly 2 service containers, no third container, no Redis/queues/job runners, no other database, no always-on compute.

## Defaults (follow unless you have a good reason, then say why)

- Work on the next unchecked commit in `08-a2-plan.md`. You may touch any file it reasonably needs (tests, imports, configs); list them in your summary.
- Fixing a failing test, a lint error or a small bug you find on the way is fine. Bigger improvements or out-of-plan features: propose first, build after Javi says yes.
- New dependencies: the ones named in `08-a2-plan.md` are pre-approved. Anything else, ask first. Soft cap ~12 per service.
- Raw SQL with `pymssql`, no ORM (learnability, see ADR). Ask before changing this.
- Keep math in pure functions, I/O in separate files. Keep the names from `05-logic-spec.md`.
- Short functions, comments explain why. Readable over clever.
- Run tests, lint and `docker compose up --build` yourself when relevant, and report results honestly.
- Do not invent API details (Jev, Polymarket, Azure, GitHub Actions). If unsure, say so and point to the docs.

## After every commit, give Javi

1. **Explain-back**: 3 to 6 bullets on how it works, with real names, plain language. For Dockerfiles and workflows, explain what each block does.
2. **A worked example** if math or a data flow was added.
3. **A draft AI_USAGE.md row** (Date/commit, Tool, Prompt, Disposition). Last column: `TODO: Javi writes this`.
4. **2 quiz questions** about what changed.

## Tone

Direct, informal, plain language. Bullets over paragraphs. No em dashes.
