import json
from pathlib import Path

# Anchored to this file, not the shell's current folder, so tests and
# python app.py find the fixture from anywhere.
FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "resolved_markets.json"


class FixtureSource:
    def fetch(self):
        with open(FIXTURE_PATH) as f:
            return json.load(f)
