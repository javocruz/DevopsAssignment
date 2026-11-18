import os
from dataclasses import dataclass

MARKET_SOURCES = ("fixture", "polymarket")
NEWS_SOURCES = ("none", "fixture", "thenewsapi")
DECIDERS = ("stub", "jev")


@dataclass(frozen=True)
class Settings:
    port: int
    data_dir: str
    log_level: str
    admin_token: str
    market_source: str
    polymarket_limit: int
    news_source: str
    thenewsapi_token: str
    news_articles: int
    news_max_calls_per_run: int
    decider: str
    typesafe_api_key: str
    typesafe_base_url: str
    jev_model: str
    http_timeout: float
    estimate_batch_limit: int
    edge_threshold: float
    min_confidence: float
    min_info: float
    base_stake: float
    max_stake: float


def read_str(name, default):
    return os.environ.get(name, default)


def read_int(name, default):
    raw = os.environ.get(name, str(default))
    try:
        return int(raw)
    except ValueError:
        raise ValueError(f"{name} must be a whole number, got {raw!r}")


def read_float(name, default):
    raw = os.environ.get(name, str(default))
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"{name} must be a number, got {raw!r}")


def read_choice(name, default, allowed):
    value = os.environ.get(name, default)
    if value not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {value!r}")
    return value


def read_stake(name, default):
    value = read_float(name, default)
    if value < 0:
        raise ValueError(f"{name} must not be negative, got {value}")
    return value


# size_stake divides by this. Zero crashes, and a negative threshold lets
# almost every edge through and produces a negative stake.
def read_threshold(name, default):
    value = read_float(name, default)
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0, got {value}")
    return value


# Reads the environment on every call so tests can change vars without a restart.
def get_settings():
    return Settings(
        port=read_int("PORT", 8000),
        data_dir=read_str("DATA_DIR", "./data"),
        log_level=read_str("LOG_LEVEL", "INFO"),
        admin_token=read_str("ADMIN_TOKEN", ""),
        market_source=read_choice("MARKET_SOURCE", "fixture", MARKET_SOURCES),
        polymarket_limit=read_int("POLYMARKET_LIMIT", 50),
        news_source=read_choice("NEWS_SOURCE", "fixture", NEWS_SOURCES),
        thenewsapi_token=read_str("THENEWSAPI_TOKEN", ""),
        news_articles=read_int("NEWS_ARTICLES", 3),
        news_max_calls_per_run=read_int("NEWS_MAX_CALLS_PER_RUN", 20),
        decider=read_choice("DECIDER", "stub", DECIDERS),
        typesafe_api_key=read_str("TYPESAFE_API_KEY", ""),
        typesafe_base_url=read_str("TYPESAFE_BASE_URL", "https://api.typesafe.ai/v1/systemone"),
        jev_model=read_str("JEV_MODEL", "jev-latest"),
        http_timeout=read_float("HTTP_TIMEOUT", 10),
        estimate_batch_limit=read_int("ESTIMATE_BATCH_LIMIT", 20),
        edge_threshold=read_threshold("EDGE_THRESHOLD", 0.08),
        min_confidence=read_float("MIN_CONFIDENCE", 0.6),
        min_info=read_float("MIN_INFO", 0.4),
        base_stake=read_stake("BASE_STAKE", 10),
        max_stake=read_stake("MAX_STAKE", 50),
    )
