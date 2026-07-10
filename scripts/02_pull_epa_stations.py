"""
Pull station (site) metadata from the EPA Water Quality Portal for NH/VT/ME
lake sites, to get latitude/longitude for each MonitoringLocationIdentifier
that appears in the Secchi depth results pulled in step 01.

Output: data/raw/epa_stations_raw.csv
"""
import requests
import pandas as pd
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUT_PATH = PROJECT_DIR / "data" / "raw" / "epa_stations_raw.csv"

STATES = {
    "NH": "US:33",
    "VT": "US:50",
    "ME": "US:23",
}

BASE_URL = "https://www.waterqualitydata.us/data/Station/search"


def pull_state(state_code: str) -> pd.DataFrame:
    params = {
        "statecode": state_code,
        "siteType": "Lake, Reservoir, Impoundment",
        "mimeType": "csv",
        "zip": "no",
    }
    resp = requests.get(BASE_URL, params=params, timeout=300)
    resp.raise_for_status()
    tmp_path = PROJECT_DIR / "data" / "raw" / f"_tmp_stations_{state_code}.csv"
    tmp_path.write_bytes(resp.content)
    df = pd.read_csv(tmp_path, low_memory=False)
    tmp_path.unlink()
    return df


def main():
    frames = []
    for abbr, code in STATES.items():
        print(f"Pulling station metadata for {abbr} ...")
        df = pull_state(code)
        print(f"  -> {len(df)} stations")
        frames.append(df)

    all_df = pd.concat(frames, ignore_index=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved {len(all_df)} total station rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
