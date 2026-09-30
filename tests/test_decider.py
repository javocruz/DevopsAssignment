import copy
import json
from pathlib import Path

import httpx

from config import get_settings
from intel.decider import JevDecider, StubDecider, get_decider, parse_jev_response

JEV_SAMPLE = json.loads((Path(__file__).parent / "data" / "jev_sample.json").read_text())


def test_stub_is_deterministic_and_in_range():
    stub = StubDecider()
    first = stub.decide("fx-ecb-cut", "ignored", 0.62)
    second = stub.decide("fx-ecb-cut", "other text", 0.62)
    assert first == second
    assert 0.01 <= first.jev_prob <= 0.99
    assert 0.3 <= first.info_score <= 0.9
    assert 0.5 <= first.confidence <= 0.9
    assert first.category == "other"


def test_parse_jev_sample():
    decision = parse_jev_response(JEV_SAMPLE)
    answers = JEV_SAMPLE["answers"]
    assert decision.jev_prob == float(answers["resolves_yes"]["probabilities"]["yes"])
    assert decision.info_score == float(answers["info_level"]["score"]) / 4
    assert decision.confidence == float(answers["resolves_yes"]["confidence"])
    assert decision.category == answers["category"]["choice"]
    assert 0 < decision.jev_prob < 1


def test_score_three_becomes_info_score_point_seventy_five():
    payload = copy.deepcopy(JEV_SAMPLE)
    payload["answers"]["info_level"]["score"] = 3.0
    assert parse_jev_response(payload).info_score == 0.75


def test_jev_without_key_falls_back_to_stub(monkeypatch):
    monkeypatch.setenv("DECIDER", "jev")
    monkeypatch.setenv("TYPESAFE_API_KEY", "")
    decider = get_decider(get_settings())
    assert isinstance(decider, StubDecider)
    assert decider.name == "stub"


def test_jev_decider_sends_bearer_and_three_questions():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=JEV_SAMPLE)

    decider = JevDecider(
        api_key="test-key",
        base_url="https://api.typesafe.ai/v1/systemone",
        model="jev-latest",
        timeout=5,
        transport=httpx.MockTransport(handler),
    )
    state_text = "Question: Will the ECB cut interest rates?"
    decision = decider.decide("fx-ecb-cut", state_text, 0.62)
    assert 0 < decision.jev_prob < 1
    request = seen[0]
    assert request.headers["Authorization"] == "Bearer test-key"
    body = json.loads(request.content)
    assert body["state"] == state_text
    assert set(body["questions"]) == {"resolves_yes", "info_level", "category"}
    assert "market_price" not in body
    assert 0.62 not in body.values()
