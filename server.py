from typing import TypedDict
from urllib.parse import quote

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

mcp = MCPServer("energy-emissions")

ENVIROFACTS_URL = "https://data.epa.gov/efservice"
FIRST_YEAR = 2010
LATEST_YEAR = 2023  # Envirofacts lags: 2024 queries returned no rows in Oct 2026

# Supplier sectors report their customers' downstream emissions, so only these
# direct-emitter sectors (from PUB_DIM_SECTOR) count toward a facility's total.
DIRECT_EMITTER_SECTORS = {
    2: "Waste",
    3: "Power Plants",
    4: "Refineries",
    5: "Chemicals",
    6: "Metals",
    7: "Pulp and Paper",
    8: "Minerals",
    14: "Other",
    15: "Petroleum and Natural Gas Systems",
}

# Excluded to match GHGRP's own facility totals.
BIOGENIC_CO2_GAS_ID = 8

COUNTY_SUFFIXES = (" COUNTY", " PARISH", " BOROUGH", " CENSUS AREA", " MUNICIPALITY", " CITY")


class Facility(TypedDict):
    facility_id: int
    name: str
    city: str
    county: str
    industry: str
    co2e_tonnes: int


# A TypedDict return type becomes the tool's output schema.
class FacilityEmissions(TypedDict):
    place: str
    year: int
    facility_count: int
    total_co2e_tonnes: int
    facilities: list[Facility]
    source: str
    query_url: str


def fetch_json(url: str) -> list | dict:
    """Single choke point so retries, caching and throttling can be added in one place."""
    response = httpx.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def normalize_county(county: str) -> str:
    """Envirofacts stores counties as e.g. 'KING COUNTY'."""
    county = county.strip().upper()
    if not county.endswith(COUNTY_SUFFIXES):
        county += " COUNTY"
    return county


def build_query_url(state: str, county: str | None, year: int) -> str:
    # Envirofacts joins tables named in one path on their shared columns.
    filters = f"state/{state}/year/{year}"
    if county:
        filters += f"/county/{quote(county)}"
    return f"{ENVIROFACTS_URL}/PUB_DIM_FACILITY/{filters}/PUB_FACTS_SECTOR_GHG_EMISSION/JSON"


def summarize_facilities(rows: list[dict]) -> list[Facility]:
    facilities: dict[int, dict] = {}
    for row in rows:
        sector = DIRECT_EMITTER_SECTORS.get(row["sector_id"])
        if sector is None or row["gas_id"] == BIOGENIC_CO2_GAS_ID or row["co2e_emission"] is None:
            continue
        facility = facilities.setdefault(
            row["facility_id"],
            {
                "facility_id": row["facility_id"],
                "name": row["facility_name"],
                "city": row["city"],
                "county": row["county"],
                "industry": [],
                "co2e_tonnes": 0.0,
            },
        )
        facility["co2e_tonnes"] += row["co2e_emission"]
        if sector not in facility["industry"]:
            facility["industry"].append(sector)

    for facility in facilities.values():
        facility["co2e_tonnes"] = round(facility["co2e_tonnes"])
        facility["industry"] = ", ".join(facility["industry"])
    return sorted(facilities.values(), key=lambda f: f["co2e_tonnes"], reverse=True)


@mcp.tool()
def get_facility_emissions(
    state: str,
    county: str | None = None,
    year: int = LATEST_YEAR,
    limit: int = 25,
) -> FacilityEmissions:
    """Get greenhouse gas emissions for large industrial facilities in a US
    state or county, from the EPA Greenhouse Gas Reporting Program (GHGRP).

    Use this for questions like "what are the biggest emitters in Harris
    County, TX?" or "total reported facility emissions in Ohio in 2022".
    Results are sorted largest emitter first.

    Do not use this for a place's total emissions footprint: GHGRP covers only
    facilities emitting over 25,000 tonnes CO2e a year (power plants,
    refineries, factories, landfills), not homes, vehicles or small businesses.

    Args:
        state: Two-letter state code, e.g. "TX".
        county: Optional county name, e.g. "Harris" or "Orleans Parish". Leave
            empty for the whole state.
        year: Reporting year, 2010 to 2023. Defaults to 2023, the latest.
        limit: Maximum facilities to list, 1 to 100. Totals always cover every
            matching facility, even those beyond the limit.

    Returns totals in metric tons of CO2-equivalent (direct emissions, excluding
    biogenic CO2 and fuel suppliers, matching GHGRP's own facility totals),
    plus the source and query URL to cite.
    """
    state = state.strip().upper()
    if len(state) != 2 or not state.isalpha():
        raise ToolError(f"'{state}' is not a two-letter state code. Use a code like 'CA' or 'TX'.")
    if not FIRST_YEAR <= year <= LATEST_YEAR:
        raise ToolError(f"GHGRP data covers {FIRST_YEAR} to {LATEST_YEAR}. Pick a year in that range.")
    limit = max(1, min(limit, 100))
    county = normalize_county(county) if county else None

    url = build_query_url(state, county, year)
    try:
        rows = fetch_json(url)
    except httpx.HTTPError as error:
        raise ToolError(f"The EPA Envirofacts API did not answer ({error}). Try again in a minute.")

    facilities = summarize_facilities(rows)
    place = f"{county.title()}, {state}" if county else state
    if not facilities:
        raise ToolError(
            f"No GHGRP facilities found for {place} in {year}. Check the county spelling, "
            "try the whole state without a county, or try another year."
        )

    return {
        "place": place,
        "year": year,
        "facility_count": len(facilities),
        "total_co2e_tonnes": sum(f["co2e_tonnes"] for f in facilities),
        "facilities": facilities[:limit],
        "source": "EPA GHGRP via Envirofacts (PUB_DIM_FACILITY joined with PUB_FACTS_SECTOR_GHG_EMISSION)",
        "query_url": url,
    }


if __name__ == "__main__":
    mcp.run()
