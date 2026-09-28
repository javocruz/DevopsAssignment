# 07 - Learning guide

Goal: Javi can explain every part of Edgebook on paper, closed-book.
Agents: after each commit, run the explain-back from here. Ask the matching questions, let Javi answer first, then correct.

## The whole thing in 30 seconds

- **Pipeline:** fetch markets -> gather news -> ask Jev -> decide bets -> settle bets -> score Jev
- **Intel** does the first three. **Book** does the last three.
- **The seam:** `Estimate` + `Resolution` in `contracts.py`. Book never imports Intel. Only `pipeline.py` imports both.
- **Default mode:** fixture markets + fixture news + stub decider, so it runs offline with zero config.
- **Headline result:** Brier score of Jev (with and without news) vs the market's, on the same resolved markets.

## Glossary (say each in one line)

| Term | One-liner |
|---|---|
| Prediction market | Yes/No question where the Yes price (0 to 1) is the crowd's probability |
| Jev | TypeSafe's model: state in, typed answers + probabilities out |
| State | what Jev reads: `build_state()` makes a dict, `render_state()` turns it into text |
| context_level | `basic` (no news) or `news` (headlines included). Scored separately |
| state_json | the exact state dict saved on every estimate, the audit trail |
| Schema version | `PRAGMA user_version`, tells `init_db()` if the DB matches the code |
| Idempotent | running it twice changes nothing the second time (UNIQUE + INSERT OR IGNORE) |
| Estimate | one Jev call's result for one market at one price snapshot |
| Edge | `jev_prob - market_price` |
| Paper bet | fake bet, fake money, real math |
| Entry price | Yes price for YES bets, `1 - Yes price` for NO bets |
| Brier score | mean squared error of probabilities vs 0/1 outcomes, lower is better |
| Calibration | when you say 70%, does it happen ~70% of the time? |
| Look-ahead bias | accidentally letting the model see info from the future, fakes good results |
| Stub decider | fake deterministic Jev so the app runs with no key |
| Fixture | bundled JSON of already-resolved markets for offline, repeatable runs |

## Worked examples to do by hand (no calculator is fine)

1. jev 0.75, market 0.60. Edge? Side? Entry price? Stake (threshold 0.08, base 10, max 50)?
   -> +0.15, YES, 0.60, 18.75
2. Same bet, outcome Yes. Shares? P&L? -> 31.25 shares, +12.50
3. jev 0.30, market 0.45. Side and entry? -> NO at 0.55
4. Brier for probs [0.8, 0.3, 0.6] outcomes [1, 0, 0] -> 0.1633
5. Why is always predicting 0.5 worth 0.25 Brier? -> (0.5)² = 0.25 every time

## Explain-back routine (end of every coding day, 15 min)

1. Close the editor.
2. On paper: draw today's piece and where it sits in the pipeline.
3. Write the function names added today and one line each on what they do.
4. Answer the day's questions below.
5. Anything fuzzy -> ask the agent to explain it again, then write your own version into the AI_USAGE.md last column.

## Questions by day

### Mon (config, app, DB)
- What does `get_settings()` return and what happens when `PORT` isn't set?
- Why bind to `0.0.0.0` and not `127.0.0.1`?
- Why `CREATE TABLE IF NOT EXISTS` and not a migration step?
- Where exactly is the SQLite file and how would you move it?

### Mon extra
- What does `PRAGMA user_version` do in `init_db()` and why not just `CREATE TABLE IF NOT EXISTS`?
- Why one SQLite connection per request?
- What happens at startup if `EDGE_THRESHOLD=abc`? And if `TYPESAFE_API_KEY` is missing?

### Tue (contracts, sources)
- What fields are in `Estimate`? Why each one?
- Why is Book not allowed to import Intel? Where would you split into microservices?
- What's the difference between FixtureSource and PolymarketSource?
- What is weird about `outcomePrices` and how does `parse_gamma_market` handle it?

### Wed (deciders, news, estimates, schema)
- What 3 things do we ask Jev in one call, and which primitive is each?
- How does `info_level.score` become `info_score`? (score / 4)
- Why is `confidence` on a yes/no Choice related to how far `jev_prob` is from 0.5?
- What does `filter_news_before` do, and why run it if the API already filters?
- Why is the TheNewsAPI token a logging risk and how did you handle it?
- How do you avoid burning the 100 news calls/day?
- Why does `build_state` never include `outcome` or `yes_price`?
- Why `hashlib.sha256` and not `hash()` in the stub?
- What happens when `DECIDER=jev` but there's no key?
- Explain your ADR 3 decision and draw the DB diagram.

### Thu (strategy, settlement, pipeline)
- Walk one bet from an Estimate to a settled P&L, with numbers.
- What 3 conditions must be true to place a bet?
- What stops a single market eating the whole bankroll?
- What happens if you call auto-bet twice?

### Fri (scoring, tests)
- What does Brier measure and what does a lower score mean?
- How does `calibration_buckets` put 1.0 in a bucket?
- What did you test heavily, what thinly, and why? (ADR 4)
- What's your coverage and what command produces it?

### Sat (security, dashboard, docs)
- What does `ADMIN_TOKEN` protect, and what happens when it's empty?
- Why `hmac.compare_digest` instead of `==`?
- Draw the architecture diagram from memory.
- List every env var and its default.
- What did you choose not to build and why? (ADR 5)

## Final quiz bank (practice Sunday, answer on paper)

1. Trace one fixture market from JSON to its row in the scorecard.
2. Where is the seam between your two domains, and what crosses it?
3. What would change in your code if Intel and Book became two services?
4. Why store price snapshots separately (or your ADR 3 choice)?
5. Compute P&L for: NO bet, stake 20, market Yes price 0.30, outcome No.
   -> entry 0.70, shares 28.57, pnl +8.57
6. Compare Jev's Brier to the market's in your actual run. What does it mean?
7. Name one AI suggestion you rejected or modified, and why.
8. How does the app behave with no env vars and no internet?
9. Why no ORM?
10. Which of your functions are pure, and why does that matter for testing?
11. Did news make Jev better calibrated? Quote your two Brier scores.
12. What happens to your DB in a container restart, and what's the fix?
13. How would you prove Jev never saw the outcome? (state_json + test)
