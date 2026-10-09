# NHDES Environmental Monitoring Database extracts: Squam Lake and Little Squam Lake

Physical/chemical grab sample (non-restricted) data from the New Hampshire Department of Environmental
Services (NHDES) Environmental Monitoring Database (EMD), for Squam Lake and Little Squam Lake.
These are the three extracts used in the manuscript *Water Clarity, Phosphorus, and Common Loon Chick
Survival on Squam Lake, New Hampshire* (F. Gajarsa, submitted to the American Journal of Student Research).

Source: <https://www.des.nh.gov/resource-center/data-and-mapping/EMD>

## Files (unmodified, exactly as provided by NHDES)

| File | Waterbody | Sample dates | Rows | Stations | Last record modified |
|---|---|---|---|---|---|
| `GrabSample_PhysChem_Squam_Before2000.xlsx` | Squam Lake | 1979-02-21 to 1999-09-06 | 28,615 | 27 | 2025-09-26 |
| `GrabSample_PhysChem_Squam_2000-2026.xlsx` | Squam Lake | 2000-01-01 to 2024-10-29 | 89,963 | 30 | 2025-10-27 |
| `GrabSample_PhysChem_LittleSquam.xlsx` | Little Squam Lake | 1979-02-22 to 2024-10-22 | 21,682 | 12 | 2025-08-20 |

Together: 140,260 result rows (one row per analyte result), including 9,963 Secchi disk transparency
readings, 8,753 chlorophyll a, 7,175 true color, 7,113 total phosphorus and 1,444 chloride results.

Each workbook has one sheet. Rows 1-2 hold the NHDES title and its data-use notice, and the column
headers are in row 5 (read with `pandas.read_excel(..., header=4)`). The columns after `Date Last Modified`
are NHDES project-membership flags; their headers name the NHDES project managers, as in the original export.

SHA-256 checksums:

```
5bd4719aae0ba5cf0df156882b63e4308293f24cbe75f1379930711f0e49e080  GrabSample_PhysChem_LittleSquam.xlsx
d367e9d7e3dbfb13769f92506cb330aafd208f94703f7eb26fccaa572c10073d  GrabSample_PhysChem_Squam_2000-2026.xlsx
e3a3817c83a046dbe80b1ff6344dbdf203c7ffb6d3d62a8150bffe479d03884c  GrabSample_PhysChem_Squam_Before2000.xlsx
```

## NHDES data-use notice (reproduced from row 2 of each file)

> NHDES recommends contacting the project manager(s) listed in this output file before using any of the
> downloaded data. The data in this database comes from multiple programs that use a variety of methods to
> satisfy many different objectives. Therefore, methods used to collect the data may not be compatible with
> your intended use of the data. Please see https://www.des.nh.gov/resource-center/data-and-mapping/EMD for
> more information about using this data. Data used in publications, presentations, etc. should be properly cited.

## Citation

New Hampshire Department of Environmental Services. Physical/chemical grab sample (non-restricted) data
from the Environmental Monitoring Database: Squam Lake and Little Squam Lake, 1979-2024 [dataset].
Concord (NH): New Hampshire Department of Environmental Services; data extract provided on request,
records modified through 2025 Oct 27.

## How the manuscript used these data

- **Comparison with the Squam Lakes Association (SLA) record.** SLA and NHDES Secchi readings were matched
  by station and date: 851 station-date pairs at 19 stations, r = 0.999, 97.5% identical within 0.05 m.
  The NHDES database therefore carries the same long-term monitoring record at these stations and adds
  later years, additional parameters and station coordinates.
- **Territory matching.** Station coordinates were used to match loon territories to the nearest station.
- **Secchi rules.** Negative values and readings with a ">" qualifier were excluded. Readings flagged as
  bottom-visible only in the comments field (neither negative nor ">") were retained; excluding them changes
  the territory-level binomial coefficient from 0.178 to 0.176 (p = 0.076 to 0.080).
- **Other parameters.** Total phosphorus (reported in ug/L; mg/L values multiplied by 1,000), chlorophyll a
  (uncorrected for pheophytin), true color and chloride were taken from the same files.
