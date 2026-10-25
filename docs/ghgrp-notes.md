# GHGRP on Envirofacts: what the tables hold

Explored 2026-10-25.

## Tables used

| Table | Grain | Key columns |
|---|---|---|
| `PUB_DIM_FACILITY` | one row per facility per year | `facility_id`, `year`, `facility_name`, `city`, `state`, `county` (e.g. `KING COUNTY`), `county_fips`, `naics_code`, `parent_company`, lat/long |
| `PUB_FACTS_SECTOR_GHG_EMISSION` | one row per facility, year, sector, subsector and gas | `facility_id`, `year`, `sector_id`, `subsector_id`, `gas_id`, `co2e_emission` (metric tons CO2e) |
| `PUB_DIM_SECTOR` | lookup | `sector_id`, `sector_name`, `sector_type` (`E` emitter, `S` supplier, `I` injection) |
| `PUB_DIM_GHG` | lookup | `gas_id`, `gas_code` (1 CO2, 2 CH4, 3 N2O, 8 biogenic CO2, ...) |

## Joining

Putting two tables in one URL path makes Envirofacts join them on their shared
columns (`facility_id` and `year`), with filters applied to the first table:

```
https://data.epa.gov/efservice/PUB_DIM_FACILITY/state/WA/year/2023/county/KING%20COUNTY/PUB_FACTS_SECTOR_GHG_EMISSION/JSON
```

## Gotchas that shape the tool

- **No facility total column.** Totals must be summed from the facts rows.
- **Suppliers are not emitters.** Sector types `S` (fuel and gas suppliers) report
  the emissions their customers cause when burning what they sell. In King County,
  WA (2023) the gas utility reports 5.7M t as a supplier, more than every emitter in
  the county combined. The tool counts only `E` sectors.
- **Biogenic CO2 (`gas_id` 8)** is reported but excluded from GHGRP's own totals
  (e.g. Cedar Hills landfill: 249k t direct, plus 57k t biogenic).
- **Some rows are null** (a supplier with no emissions); skip them.
- **Counties are stored uppercase with a suffix** (`KING COUNTY`, `ORLEANS PARISH`).
- **`ROWS/a:b` paginates rows, not facilities**, so a facility limit has to be
  applied after summing, not in the URL.
- **Latest year is 2023.** Queries for 2024 return `[]` as of Oct 2026.
