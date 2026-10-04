# Architecture Decision Records

Five entries, added on the day each decision is made.

## [1]. Backend framework
Date: 2026-09-28
Status: Decided
Context: Edgebook is one Python process with SQLite and JSON routes. It needs a web framework, and the database connection cannot be shared across requests.
Decision: I chose FastAPI. It checks request data and serves /docs on its own, and Depends fits get_db: one SQLite connection per request, opened and closed for me.
Alternatives considered: Django. It pushes an ORM, and this project uses plain sqlite3 on purpose. It is also a lot of framework for one small app.
Consequences: Routes can use Depends(get_db), and /docs is free. The cost is that I have to be able to explain a FastAPI dependency, and routes stay plain def rather than async.

## [2]. Intel / Book domain split
Date: 2026-09-29
Status: Decided
Context: The assignment wants two feature domains that could each become a service, and exactly one SQLite file.
Decision: I split the app into two packages, intel and book, that only share the Estimate and Resolution records in contracts.py. News goes inside intel because it is just extra context for an estimate.
Alternatives considered: One package for everything: simpler now, but I could not split intel and book into two services later without rewriting both. Two database files already: the assignment wants one SQLite path, so that waits until A2. News as a third domain: it is only context for estimates, so it would add work without adding a real feature.
Consequences: Everything stays in one SQLite file for now, but no foreign key crosses the seam, so each domain can get its own database in A2. The cost is that pipeline.py has to do the glue work between them.

## [3]. SQLite schema
Date: 2026-10-01
Status: Decided
Context: An estimate is judged against the Yes price at that moment. A market gets new prices later. One price column on the market row would be replaced, and the edge would no longer match what Jev was asked.
Decision: I put yes_price on price_snapshots, together with captured_at, instead of on markets. estimates.snapshot_id points at that row, so the edge uses the price from estimate time.
Alternatives considered: A yes_price column on markets. That is one less table, but the next sync overwrites the price Jev was compared with, so the edge is no longer honest. No foreign keys on bets, PRAGMA user_version, and state_json are also in the schema. This ADR is only about where the price lives.
Consequences: list_estimate_records joins price_snapshots to read market_price. That price is the one from the estimate, not a later sync. The cost is an extra table and that join. A market can keep every price it has had.

## [4]. Testing approach
Date: 2026-10-02
Status: Decided
Context: The grade asks for pytest on the core logic and at least 70% coverage. The quiz asks which parts were tested heavily and which were left thin.
Decision: I test the math and the parsers hard: compute_edge, should_bet, size_stake, settle_bet, brier_score, calibration_buckets, parse_jev_response, and filter_news_before. Jev, Polymarket, and TheNewsAPI are tested only with httpx.MockTransport and saved samples. Routes are tested only enough to show the pipeline connects.
Alternatives considered: Testing every route and error branch equally. That lifts the coverage number, but the formulas are what I have to explain, and a live API call in a test needs a key and fails offline.
Consequences: The coverage command and the number live in the README. app.py startup and some error branches stay thin on purpose.

## [5]. What I chose not to build
Date: 2026-10-04
Status: Decided
Context: The assignment leaves out real orders, user accounts, and a scheduler. On the 35 fixture markets the market Brier was 0.136 and Jev's was about 0.210. Five paper bets lost 50.04. I still wanted the desk to be something I could trust with money later.
Decision: I keep paper bets only. There is one optional ADMIN_TOKEN instead of accounts. Nothing runs on a timer. Real orders wait until a new batch of markets beats the market on Brier.
Alternatives considered: Lowering EDGE_THRESHOLD, MIN_CONFIDENCE, or MIN_INFO to place more bets on these same 35 markets. That would bet the forecasts should_bet already skipped, after I had seen the outcomes. Adding another information source. News barely moved Jev, and a new feed is another dependency and another look-ahead risk. Accounts and a scheduler. Neither one changes jev_prob. They only add login and a clock.
Consequences: place_bets still writes paper rows, and settle_bet still scores them. The cost is that the app does not trade, does not know who the user is, and does not run unless someone presses the button.

<!--
Format (copy for each entry):

## [N]. <Title>
Date: YYYY-MM-DD
Status: Decided
Context: 1-3 sentences, what forced this decision
Decision: 1-2 sentences, what you chose
Alternatives considered: at least one real alternative, and why you rejected it
Consequences: 1-2 sentences, what this costs or enables later

Planned entries:
1. Backend framework (Mon Sep 28)
2. Intel / Book domain split (Tue Sep 29)
3. SQLite schema decision (Thu Oct 1)
5. What I chose not to build (Sun Oct 4)
-->
