"""
Step 1: Pull in-situ Secchi depth measurements from the EPA Water Quality Portal
(waterqualitydata.us) for lakes in NH, VT, and ME. This is the training data
for the regional water clarity model.

Output: data/raw/epa_secchi_raw.csv
"""
import requests
import pandas as pd
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUT_PATH = PROJECT_DIR / "data" / "raw" / "epa_secchi_raw.csv"

STATES = {
    "NH": "US:33",
    "VT": "US:50",
    "ME": "US:23",
}

# Secchi depth characteristic names used in the Water Quality Portal
# (confirmed via https://www.waterqualitydata.us/Codes/characteristicname?text=secchi)
CHARACTERISTIC_NAMES = ["Depth, Secchi disk depth", "Water transparency, Secchi disc"]

BASE_URL = "https://www.waterqualitydata.us/data/Result/search"


def pull_state(state_code: str) -> pd.DataFrame:
    params = {
        "statecode": state_code,
        "characteristicName": CHARACTERISTIC_NAMES,
        "siteType": "Lake, Reservoir, Impoundment",
        "sampleMedia": "Water",
        "mimeType": "csv",
        "zip": "no",
    }
    resp = requests.get(BASE_URL, params=params, timeout=300)
    resp.raise_for_status()
    tmp_path = PROJECT_DIR / "data" / "raw" / f"_tmp_{state_code}.csv"
    tmp_path.write_bytes(resp.content)
    df = pd.read_csv(tmp_path, low_memory=False)
    tmp_path.unlink()
    return df


def main():
    frames = []
    for abbr, code in STATES.items():
        print(f"Pulling Secchi depth data for {abbr} ...")
        df = pull_state(code)
        df["StateAbbr"] = abbr
        print(f"  -> {len(df)} results")
        frames.append(df)

    all_df = pd.concat(frames, ignore_index=True)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_df.to_csv(OUT_PATH, index=False)
    print(f"\nSaved {len(all_df)} total rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
