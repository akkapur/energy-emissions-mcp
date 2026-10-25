# energy-emissions-mcp

An MCP server that exposes US energy and emissions data as tools an AI agent can call.

It currently has one tool, `get_facility_emissions`, which answers questions like
"who are the biggest emitters in Harris County, TX?" from the EPA Greenhouse Gas
Reporting Program (GHGRP), queried live through the
[Envirofacts API](https://www.epa.gov/enviro/envirofacts-data-service-api). No API key needed.

## Run it

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run mcp dev server.py        # opens MCP Inspector to call the tool by hand
uv run pytest                   # offline tests with recorded EPA rows
```

Add it to Claude Code:

```sh
claude mcp add energy-emissions -- uv run --directory "$PWD" mcp run server.py
```

## The tool

`get_facility_emissions(state, county=None, year=2023, limit=25)` returns each facility's
name, city, county, industry and total CO2e (metric tons), largest first, plus the place's
total, the source tables and the exact query URL so answers can cite it.

Totals are direct emissions, matching GHGRP's own facility totals: biogenic CO2 and
fuel suppliers' downstream emissions are left out. See [docs/ghgrp-notes.md](docs/ghgrp-notes.md).

Built with the [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/) v2 and httpx.
