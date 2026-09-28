import pytest

from config import get_settings

EDGEBOOK_VARS = [
    "PORT", "DATA_DIR", "LOG_LEVEL", "ADMIN_TOKEN",
    "MARKET_SOURCE", "POLYMARKET_LIMIT",
    "NEWS_SOURCE", "THENEWSAPI_TOKEN", "NEWS_ARTICLES", "NEWS_MAX_CALLS_PER_RUN",
    "DECIDER", "TYPESAFE_API_KEY", "TYPESAFE_BASE_URL", "JEV_MODEL",
    "HTTP_TIMEOUT", "ESTIMATE_BATCH_LIMIT",
    "EDGE_THRESHOLD", "MIN_CONFIDENCE", "MIN_INFO", "BASE_STAKE", "MAX_STAKE",
]


# Javi's shell may have real keys exported, so every test starts from a clean slate.
@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in EDGEBOOK_VARS:
        monkeypatch.delenv(name, raising=False)


def test_defaults_with_empty_env():
    settings = get_settings()
    assert settings.port == 8000
    assert settings.data_dir == "./data"
    assert settings.market_source == "fixture"
    assert settings.news_source == "fixture"
    assert settings.decider == "stub"
    assert settings.edge_threshold == 0.08
    assert settings.typesafe_api_key == ""
    assert settings.thenewsapi_token == ""
    assert settings.admin_token == ""


def test_port_is_read_as_int(monkeypatch):
    monkeypatch.setenv("PORT", "9000")
    assert get_settings().port == 9000


def test_bad_edge_threshold_raises(monkeypatch):
    monkeypatch.setenv("EDGE_THRESHOLD", "abc")
    with pytest.raises(ValueError, match="EDGE_THRESHOLD"):
        get_settings()


def test_unknown_decider_raises(monkeypatch):
    monkeypatch.setenv("DECIDER", "banana")
    with pytest.raises(ValueError, match="DECIDER"):
        get_settings()
