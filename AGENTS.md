# AGENTS.md

Guidance for AI coding agents working in this repo. Humans: see README.md.

## Project

An MCP server that wraps US government energy and emissions APIs as tools for AI
agents. Today it has one tool, `get_facility_emissions`, over EPA GHGRP data
from Envirofacts.

Prefer small, readable code over clever or general code.

## Layout

- `server.py`: the whole server: `fetch_json`, helpers, and the tools.
- `tests/`: offline pytest tests using recorded API rows.
- `docs/ghgrp-notes.md`: what the GHGRP tables hold and the traps in them. Read
  it before changing how emissions are summed.
- `uv.lock`: generated. Change it only through `uv add` / `uv remove`.

## Commands

- Install: `uv sync`
- Test: `uv run pytest` (run after every change to `server.py`; all must pass)
- One test: `uv run pytest tests/test_server.py -k <name>`
- Inspect by hand: `uv run mcp dev server.py` (opens MCP Inspector)
- Run over stdio: `uv run mcp run server.py`

Always go through `uv run`; never call `pip` or a bare `python`.

## Conventions

- **MCP SDK v2.** `from mcp.server import MCPServer`. `FastMCP` and
  `mcp.server.fastmcp` are v1 names and no longer exist. Check the installed
  package before copying v1 examples from the web.
- **All outbound HTTP goes through `fetch_json`.** Retries, caching and
  throttling will be added there, so tools must not call httpx directly.
- **Tool docstrings are prompts.** The model reads them to decide when and how
  to call a tool. Say what it is for, what each argument means, and when not to
  use it.
- **Errors the model should read raise `ToolError`** with one plain sentence that
  says what to try next. Any other exception reaches the model only as
  "Error executing tool".
- **Return trimmed, typed results.** Use a `TypedDict` return type (it becomes
  the tool's output schema). Never return raw API rows. Include a `source` and
  the `query_url` so answers can cite them.
- **Fix the tool, not the prompt.** When an agent misuses a tool, change its
  arguments, docstring or return shape.
- Type hints on every function, `str | None` style. Python 3.12.
- **No verbose comments.** Write a comment only when the code can't say it, and
  make it explain *why*, not *what*. Good: `# Excluded to match GHGRP's own
  totals.` Bad: `# Loop over rows and add up emissions.` Tool docstrings are
  the exception, since they are written for the model.

## Tests

- No comments in tests. A test's name says what behaviour it checks, e.g.
  `test_summarize_excludes_biogenic_co2`; one behaviour per test.
- Tests must not hit the network. Replace `server.fetch_json` with
  `monkeypatch` and feed recorded rows.
- When you add a tool, add a test that calls it through `mcp.Client(server.mcp)`
  and one for its main error path.
- When real data surprises you, record a trimmed sample as a fixture and add it
  to `docs/` notes.

## Boundaries

- Ask before adding a dependency, and pin exact versions in `pyproject.toml`.
- Don't add caching, retries, throttling or a database until the problem shows
  up.
- Never commit API keys. Keys (e.g. EIA) come from environment variables.
- Keep changes scoped to the task; no drive-by refactors.

## Git

- Branch names describe the change, e.g. `feat/facility-emissions-tool` or
  `fix/county-suffix`. Never put "claude" or other tool names in a branch name.
- PR descriptions are short and to the point: a few bullets on what changed
  and how it was tested. No restating the diff.
- This repo is public. PR descriptions, commits and docs must not include
  attribution blocks, "Generated with ..." footers, links to private tools or
  chats, or internal planning references (e.g. milestone numbers).
