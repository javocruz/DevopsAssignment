from dataclasses import dataclass


# The only records that cross between intel and book. Frozen so nobody
# mutates one mid-handoff, plain types so A2 can send them as JSON.
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
