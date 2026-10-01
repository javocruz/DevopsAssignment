# Database schema

Matches `SCHEMA_SQL` in `db.py`. ADR 3 is about `price_snapshots`: `yes_price` lives there with `captured_at`, and `estimates.snapshot_id` points at that row. `bets` has no foreign key. The dotted line is only a logical link.

`price_snapshots` is unique on `(market_id, captured_at)`. `news_items` is unique on `(market_id, url)`. `estimates` is unique on `(market_id, snapshot_id, decider, context_level)`.

```mermaid
erDiagram
    markets ||--o{ price_snapshots : has
    markets ||--o{ news_items : has
    markets ||--o{ estimates : has
    price_snapshots ||--o{ estimates : "priced at"
    estimates ||..o| bets : "logical ref (no FK)"
    markets {
        TEXT id PK
        TEXT question
        TEXT rules
        TEXT category
        TEXT end_date
        TEXT news_query
        TEXT analyst_notes
        TEXT source
        TEXT status
        INTEGER outcome
    }
    price_snapshots {
        INTEGER id PK
        TEXT market_id FK
        REAL yes_price
        TEXT captured_at
    }
    news_items {
        INTEGER id PK
        TEXT market_id FK
        TEXT title
        TEXT description
        TEXT source
        TEXT url
        TEXT published_at
        TEXT fetched_at
    }
    estimates {
        INTEGER id PK
        TEXT market_id FK
        INTEGER snapshot_id FK
        TEXT decider
        TEXT context_level
        REAL jev_prob
        REAL info_score
        REAL confidence
        TEXT category
        TEXT state_json
        TEXT created_at
    }
    bets {
        INTEGER id PK
        INTEGER estimate_id
        TEXT market_id
        TEXT decider
        TEXT context_level
        TEXT side
        REAL entry_price
        REAL stake
        REAL shares
        TEXT status
        REAL pnl
        TEXT placed_at
        TEXT settled_at
    }
```
