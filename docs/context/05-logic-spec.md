# 05 - Logic spec

Every formula here must be implemented exactly as written, as a function with the exact name shown.
Functions marked PURE take values and return values: no DB, no HTTP, no `datetime.now()`, no env vars.
If you think something should change, ask Javi first. He has to explain all of this on paper.

## contracts.py

```python
@dataclass(frozen=True)
class Estimate:
    estimate_id: int
    market_id: str
    question: str
    market_price: float   # Yes price at estimate time (from the snapshot)
    jev_prob: float       # decider's P(Yes)
    info_score: float     # 0..1
    confidence: float     # 0..1
    decider: str          # "stub" or "jev"
    context_level: str    # "basic" or "news"
    created_at: str

@dataclass(frozen=True)
class Resolution:
    market_id: str
    outcome: int          # 1 = Yes, 0 = No
    resolved_at: str
```
- `frozen=True`: nobody mutates a record while it crosses the seam.
- Only plain types: in A2 these become JSON with `dataclasses.asdict()`.

---

## Intel: market sources (`intel/sources.py`)

Both sources return a list of plain dicts:
`{"id", "question", "rules", "category", "end_date", "news_query", "yes_price", "captured_at", "status", "outcome"}`

**FixtureSource**: reads `fixtures/resolved_markets.json`. `yes_price` is from **before** resolution. `outcome` is there for settlement only.

**PolymarketSource**
- `GET https://gamma-api.polymarket.com/markets`, public, no auth. Params: `limit=POLYMARKET_LIMIT`, plus active/closed filters. **Check param names in docs.polymarket.com before coding.**
- `parse_gamma_market(raw) -> dict | None` PURE.
  - `outcomes` and `outcomePrices` are **JSON-encoded strings**: `'["Yes","No"]'`, `'["0.62","0.38"]'`. `json.loads` then `float()`.
  - `yes_price` = price at the index of `"Yes"`.
  - Not binary Yes/No -> return `None` (skipped).
  - `news_query` = `None` here, built later by `build_news_query()`.

---

## Intel: news (`intel/news.py`)

### Sources
- **FixtureNews**: headlines stored per market inside `fixtures/resolved_markets.json` (`"news": [...]`), already filtered to before `captured_at`.
- **TheNewsApi**:
  - `GET https://api.thenewsapi.com/v1/news/all`
  - params: `api_token=THENEWSAPI_TOKEN`, `search=<news_query>`, `language=en`, `published_before=<captured_at as YYYY-MM-DDTHH:MM:SS>`, `limit=NEWS_ARTICLES`, `sort=relevance_score`
  - keep from each article: `title`, `description`, `source`, `url`, `published_at`. Ignore `snippet` (only 60 chars).
  - **The token is in the URL.** Never log the URL, never put it in exceptions shown to users. `httpx` logger is set to WARNING in `app.py`.
- `get_news_source(settings)`: `none` -> no news, `fixture` -> FixtureNews, `thenewsapi` with token -> TheNewsApi, `thenewsapi` without token -> warn, FixtureNews.

### `build_news_query(question: str, max_words: int = 5) -> str` PURE
```
1. lowercase, remove punctuation (re.sub(r"[^a-z0-9 ]", " ", ...))
2. drop stopwords: will, the, a, an, of, in, on, at, by, to, be, is, before, after, end, 2025, 2026, ...
3. keep the first max_words remaining words, joined by spaces
```
If `markets.news_query` is already set (fixture, or analyst edit), use that instead.
Example: `"Will the ECB cut interest rates at its December 2026 meeting?"` -> `"ecb cut interest rates its"`. Imperfect on purpose, hand-written queries in the fixture are better.

### `filter_news_before(items: list[dict], cutoff: str, limit: int) -> list[dict]` PURE
```
keep items where item["published_at"] < cutoff
sort newest first
return the first `limit`
```
This is the **look-ahead guard**. It runs even though the API already filters, because a bad API response or fixture must never leak future news.

### Fetch budget
`fetch_news_for_markets(conn, source, markets, max_calls)`: skip markets that already have rows in `news_items`, stop after `max_calls` API calls, `INSERT OR IGNORE`.

---

## Intel: building what Jev sees (`intel/estimates.py`)

### `days_to_resolution(end_date: str, as_of: str) -> int` PURE
Whole days between the two dates, minimum 0.

### `build_state(market, snapshot, news, context_level) -> dict` PURE
```
{
  "question": market["question"],
  "rules": market["rules"],
  "category": market["category"],
  "end_date": market["end_date"],
  "as_of": snapshot["captured_at"],
  "days_to_resolution": days_to_resolution(market["end_date"], snapshot["captured_at"]),
  "analyst_notes": market["analyst_notes"],          # omitted if empty
  "headlines": [ {title, description, published_at}, ... ]   # only when context_level == "news"
}
```
**Never** includes `outcome`, `yes_price`, `status`, or any key/token. Tests enforce this.

### `render_state(state: dict) -> str` PURE
Jev's `state` field is **text**. Render labeled lines, e.g.:
```
Question: Will the ECB cut interest rates at its December 2026 meeting?
Resolution rules: ...
Category: economics
Market closes: 2026-12-17
Today: 2026-10-01 (77 days before close)
Analyst notes: ...
Recent headlines (newest first):
- 2026-09-30: ECB's Lane says inflation path "on track" | <description>
- ...
```
`state_json` stores the dict, Jev receives the rendered text.

---

## Intel: deciders (`intel/decider.py`)

```python
@dataclass(frozen=True)
class Decision:
    jev_prob: float
    info_score: float
    confidence: float
    category: str
```

### JevDecider (verified against docs.typesafe.ai on 2026-09-28)

Request:
```
POST {TYPESAFE_BASE_URL}          # https://api.typesafe.ai/v1/systemone
Authorization: Bearer {TYPESAFE_API_KEY}
Content-Type: application/json

{
  "model": "jev-latest",
  "state": "<render_state(state)>",
  "questions": {
    "resolves_yes": {
      "type": "choice",
      "instructions": "Based only on the information given, will this prediction market resolve Yes?",
      "criteria": {
        "yes": "The event described happens and the market resolves Yes",
        "no": "The event does not happen and the market resolves No"
      }
    },
    "info_level": {
      "type": "score",
      "instructions": "How much concrete, relevant information does this state contain for forecasting the outcome?",
      "criteria": [
        "None: only the question itself",
        "Very little: vague or unrelated context",
        "Some: a few relevant facts",
        "Good: several recent, relevant facts",
        "Strong: specific, recent evidence that bears directly on the outcome"
      ]
    },
    "category": {
      "type": "choice",
      "instructions": "Which category best describes this market?",
      "criteria": {"politics": null, "crypto": null, "sports": null, "economics": null, "tech": null, "other": null}
    }
  }
}
```
Response (relevant parts):
```
answers.resolves_yes.probabilities.yes   -> jev_prob
answers.resolves_yes.confidence          -> confidence
answers.info_level.score                 -> 0..4, normalized: info_score = score / 4
answers.category.choice                  -> category
```
- All 3 questions go in **one** call. Jev answers them in parallel, independently.
- Known quirk (quiz material): for a 2-option Choice, `confidence` measures how concentrated the probabilities are, so it moves with how far `jev_prob` is from 0.5. It still adds a useful gate against coin-flip answers.
- Parse into `Decision` in a small pure function `parse_jev_response(payload) -> Decision` so it can be tested with a saved payload in `tests/data/jev_sample.json`.
- `typesafe-sdk` exists but is not used: plain `httpx` keeps the request visible and mockable.

### StubDecider (deterministic, no network)
```
seed       = int(hashlib.sha256(market_id.encode()).hexdigest(), 16)
offset     = ((seed % 21) - 10) / 100        # -0.10 .. +0.10
jev_prob   = clamp(market_price + offset, 0.01, 0.99)
info_score = 0.3 + (seed % 7) / 10            # 0.3 .. 0.9
confidence = 0.5 + (seed % 5) / 10            # 0.5 .. 0.9
category   = "other"
```
- The stub is the only decider that sees `market_price` (it has no brain). Real Jev never does.
- `hashlib.sha256`, not `hash()`: `hash()` is randomized per process.

### `get_decider(settings)`
`jev` + key -> JevDecider. `jev` without key -> warning + StubDecider. Otherwise StubDecider.

### `run_estimates(conn, decider, news_source, context_level, limit, now)`
For up to `limit` markets with a snapshot and no estimate for `(market, snapshot, decider.name, context_level)`:
1. `news = filter_news_before(cached news, snapshot.captured_at, NEWS_ARTICLES)` if `context_level == "news"`, else `[]`
2. `state = build_state(...)`
3. `decision = decider.decide(state, market_price)` (JevDecider ignores `market_price`)
4. `INSERT OR IGNORE` into `estimates` with `state_json = json.dumps(state)`
5. On exception for one market: log it, append to `failed`, continue.
Returns `{"processed", "skipped", "failed"}`.

---

## Book logic (all PURE)

### 1. `compute_edge(jev_prob, market_price) -> float`
`edge = jev_prob - market_price`. Positive -> bet YES. Negative -> bet NO.

### 2. `should_bet(edge, confidence, info_score, settings) -> bool`
```
abs(edge) >= EDGE_THRESHOLD
and confidence >= MIN_CONFIDENCE
and info_score >= MIN_INFO
```

### 3. `pick_side(edge) -> str` and `entry_price(side, market_price) -> float`
```
side  = "YES" if edge > 0 else "NO"
price = market_price if side == "YES" else 1 - market_price
```

### 4. `size_stake(edge, settings) -> float`
`stake = round(min(MAX_STAKE, BASE_STAKE * abs(edge) / EDGE_THRESHOLD), 2)`
Rejected alternative: Kelly criterion (aggressive, harder to explain).

### 5. `settle_bet(side, stake, entry_price, outcome) -> tuple[str, float]`
```
shares = stake / entry_price
won    = (side == "YES" and outcome == 1) or (side == "NO" and outcome == 0)
pnl    = round(shares - stake, 2)  if won
pnl    = round(-stake, 2)          if lost
return ("won" or "lost", pnl)
```

### 6. `brier_score(probs, outcomes) -> float | None`
`sum((p - o) ** 2) / len(probs)`. Lower is better. Empty -> `None`.
Computed on the same resolved markets for `jev_prob` AND `market_price`, filtered to ONE `decider` + ONE `context_level`.

### 7. `calibration_buckets(probs, outcomes, n_buckets=10) -> list[dict]`
```
index = min(int(p * n_buckets), n_buckets - 1)     # p = 1.0 goes in the last bucket
per bucket: {"range": "0.6-0.7", "count", "avg_pred", "actual_rate"}
```
Empty buckets skipped.

---

## Shared: `security.py`

`require_admin(x_admin_token: str | None = Header(None))`:
- `ADMIN_TOKEN` empty -> allow.
- Set and header equal -> allow (compare with `hmac.compare_digest`).
- Otherwise -> `HTTPException(401)`.
Attached to every POST route. `/healthz` and GETs stay open.

---

## Worked examples (reuse in tests)

**Edge + side + stake** (threshold 0.08, base 10, max 50)
- jev 0.75, market 0.60 -> +0.15 -> YES at 0.60 -> stake 18.75
- jev 0.30, market 0.45 -> -0.15 -> NO at 0.55 -> stake 18.75
- jev 0.95, market 0.40 -> +0.55 -> stake 50 (capped)
- jev 0.63, market 0.60 -> +0.03 -> no bet

**Settlement**
- YES, 10, entry 0.40, outcome 1 -> 25 shares -> +15.00 won
- YES, 10, entry 0.40, outcome 0 -> -10.00 lost
- NO, 18.75, entry 0.55, outcome 0 -> 34.09 shares -> +15.34 won

**Brier**: probs [0.8, 0.3, 0.6], outcomes [1, 0, 0] -> 0.1633

**News filter**: cutoff `2026-10-01T00:00:00`, items published `09-29`, `09-30`, `10-02` -> keeps `09-30`, `09-29` (newest first), drops `10-02`

**Jev parse**: `info_level.score = 3.0` -> `info_score = 0.75`
