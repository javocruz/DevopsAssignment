import hashlib
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Copied from 05-logic-spec.md. All three questions go in one call.
JEV_QUESTIONS = {
    "resolves_yes": {
        "type": "choice",
        "instructions": "Based only on the information given, will this prediction market resolve Yes?",
        "criteria": {
            "yes": "The event described happens and the market resolves Yes",
            "no": "The event does not happen and the market resolves No",
        },
    },
    "info_level": {
        "type": "score",
        "instructions": "How much concrete, relevant information does this state contain for forecasting the outcome?",
        "criteria": [
            "None: only the question itself",
            "Very little: vague or unrelated context",
            "Some: a few relevant facts",
            "Good: several recent, relevant facts",
            "Strong: specific, recent evidence that bears directly on the outcome",
        ],
    },
    "category": {
        "type": "choice",
        "instructions": "Which category best describes this market?",
        "criteria": {
            "politics": None,
            "crypto": None,
            "sports": None,
            "economics": None,
            "tech": None,
            "other": None,
        },
    },
}


@dataclass(frozen=True)
class Decision:
    jev_prob: float
    info_score: float
    confidence: float
    category: str


def clamp(value, low, high):
    return max(low, min(high, value))


# Pure: numbers out of a saved payload, no HTTP.
def parse_jev_response(payload):
    answers = payload["answers"]
    return Decision(
        jev_prob=float(answers["resolves_yes"]["probabilities"]["yes"]),
        info_score=float(answers["info_level"]["score"]) / 4,
        confidence=float(answers["resolves_yes"]["confidence"]),
        category=answers["category"]["choice"],
    )


class StubDecider:
    name = "stub"

    def decide(self, market_id, state_text, market_price):
        seed = int(hashlib.sha256(market_id.encode()).hexdigest(), 16)
        offset = ((seed % 21) - 10) / 100
        return Decision(
            jev_prob=clamp(market_price + offset, 0.01, 0.99),
            info_score=0.3 + (seed % 7) / 10,
            confidence=0.5 + (seed % 5) / 10,
            category="other",
        )


class JevDecider:
    name = "jev"

    def __init__(self, api_key, base_url, model, timeout, transport=None):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.transport = transport

    def decide(self, market_id, state_text, market_price):
        body = {
            "model": self.model,
            "state": state_text,
            "questions": JEV_QUESTIONS,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
            response = client.post(self.base_url, json=body, headers=headers)
            response.raise_for_status()
            return parse_jev_response(response.json())


def get_decider(settings):
    if settings.decider == "jev" and settings.typesafe_api_key:
        return JevDecider(
            settings.typesafe_api_key,
            settings.typesafe_base_url,
            settings.jev_model,
            settings.http_timeout,
        )
    if settings.decider == "jev":
        logger.warning("DECIDER=jev but TYPESAFE_API_KEY is empty, using stub")
    return StubDecider()
