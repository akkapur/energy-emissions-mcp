import pytest
from mcp import Client

import server

RECORDED_KING_COUNTY_2023 = [
    (1002537, "ASH GROVE CEMENT COMPANY-SEATTLE", "SEATTLE", 8, 1, 366729.9),
    (1002537, "ASH GROVE CEMENT COMPANY-SEATTLE", "SEATTLE", 8, 2, 325),
    (1002537, "ASH GROVE CEMENT COMPANY-SEATTLE", "SEATTLE", 8, 3, 596),
    (1003946, "City of Enumclaw Gas Utility", "Enumclaw", 11, None, None),
    (1005387, "Puget Sound Energy LDC", "Bellevue", 11, 1, 5748212.4),
    (1005387, "Puget Sound Energy LDC", "Bellevue", 15, 1, 1060.1),
    (1005387, "Puget Sound Energy LDC", "Bellevue", 15, 2, 66418),
    (1005387, "Puget Sound Energy LDC", "Bellevue", 15, 3, 0.596),
    (1007822, "KING CNTY SOLID WST CEDAR HILLS LANDFILL", "MAPLE VALLEY", 2, 1, 191.8),
    (1007822, "KING CNTY SOLID WST CEDAR HILLS LANDFILL", "MAPLE VALLEY", 2, 2, 249007.25),
    (1007822, "KING CNTY SOLID WST CEDAR HILLS LANDFILL", "MAPLE VALLEY", 2, 3, 204.13),
    (1007822, "KING CNTY SOLID WST CEDAR HILLS LANDFILL", "MAPLE VALLEY", 2, 8, 56525.4),
]
ROWS = [
    {
        "facility_id": fid,
        "facility_name": name,
        "city": city,
        "county": "KING COUNTY",
        "sector_id": sector,
        "gas_id": gas,
        "co2e_emission": co2e,
    }
    for fid, name, city, sector, gas, co2e in RECORDED_KING_COUNTY_2023
]


def test_normalize_county_appends_county_suffix_when_missing():
    assert server.normalize_county(" king ") == "KING COUNTY"


def test_normalize_county_keeps_existing_parish_suffix():
    assert server.normalize_county("Orleans Parish") == "ORLEANS PARISH"


def test_build_query_url_joins_facility_and_emission_tables_with_encoded_county():
    assert server.build_query_url("WA", "KING COUNTY", 2023) == (
        "https://data.epa.gov/efservice/PUB_DIM_FACILITY/state/WA/year/2023"
        "/county/KING%20COUNTY/PUB_FACTS_SECTOR_GHG_EMISSION/JSON"
    )


def totals_by_facility_id():
    return {f["facility_id"]: f["co2e_tonnes"] for f in server.summarize_facilities(ROWS)}


def test_summarize_sums_all_gases_for_a_direct_emitter():
    assert totals_by_facility_id()[1002537] == 367651


def test_summarize_excludes_supplier_sector_rows():
    assert totals_by_facility_id()[1005387] == 67479


def test_summarize_excludes_biogenic_co2():
    assert totals_by_facility_id()[1007822] == 249403


def test_summarize_drops_facilities_with_no_direct_emissions():
    assert 1003946 not in totals_by_facility_id()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_tool_over_mcp_returns_place_totals_and_largest_facilities_first(monkeypatch):
    monkeypatch.setattr(server, "fetch_json", lambda url: ROWS)
    async with Client(server.mcp) as client:
        result = await client.call_tool("get_facility_emissions", {"state": "wa", "county": "King", "limit": 2})
    data = result.structured_content
    assert data["place"] == "King County, WA"
    assert data["facility_count"] == 3
    assert data["total_co2e_tonnes"] == 367651 + 67479 + 249403
    assert [f["name"] for f in data["facilities"]] == [
        "ASH GROVE CEMENT COMPANY-SEATTLE",
        "KING CNTY SOLID WST CEDAR HILLS LANDFILL",
    ]


@pytest.mark.anyio
async def test_empty_result_is_a_readable_error(monkeypatch):
    monkeypatch.setattr(server, "fetch_json", lambda url: [])
    async with Client(server.mcp) as client:
        result = await client.call_tool("get_facility_emissions", {"state": "WA", "county": "Nowhere"})
    assert result.is_error
    assert "No GHGRP facilities found for Nowhere County, WA" in result.content[0].text
