# AI Usage Log

One entry per meaningful AI interaction. The bold labels are the required columns. The last one is mine: how the code works, in my own words, using the real function and variable names.

## 2026-09-28 / C0

**Tool:** Claude

**Prompt:** Turn the Edgebook plan into repo context files for my coding agents, split by topic, with a per-commit plan.

**Disposition (Accepted / Modified / Rejected):** Modified

**What changed & why:** Added the Edgebook context docs (`docs/context/01` to `07`), `AGENTS.md`, `CLAUDE.md`, `README.md`, `ADR.md`, `AI_USAGE.md`, and `.gitignore`. Before the final push, `AGENTS.md` gained the rule that agents stop and ask, and commit messages gained the `C0:` / `C1:` prefix.

**In my own words, how this works:**
Hello! what i did for this first push was add my whole repo idea into various context and .MD files, it sets limits on how we are builidng things. i added the lists of commits that im planning, setting the limits where im working and making a log of the decisions im making. excited to start the project!!


## 2026-09-28 / C1

**Tool:** Cursor

**Prompt:** Implement C1, validated config that reads every env var, with offline defaults, pinned dependencies, and config tests.

**Disposition (Accepted / Modified / Rejected):** Modified

**What changed & why:** Added `config.py`, `requirements.txt`, and `tests/test_config.py`. Also added `pytest.ini` so plain `pytest` can import `config`.

**In my own words, how this works:**
i added config.py so get_settings reads my settings from the environment. if PORT is not set, port is 8000. if TYPESAFE_API_KEY is missing, it stays an empty string and the app still starts. pytest.ini lets me run plain pytest so it can import config. all of these things are being set up to prevent future errors, and making everything cleaner

