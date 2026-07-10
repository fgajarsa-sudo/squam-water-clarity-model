"""
Clean and merge the raw EPA Secchi results with station lat/lon metadata
to produce a single training table: one row per in-situ Secchi reading,
with site coordinates, ready to match against Landsat imagery.

Output: data/processed/insitu_secchi_clean.csv
"""
import pandas as pd
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
RESULTS_PATH = PROJECT_DIR / "data" / "raw" / "epa_secchi_raw.csv"
STATIONS_PATH = PROJECT_DIR / "data" / "raw" / "epa_stations_raw.csv"
OUT_PATH = PROJECT_DIR / "data" / "processed" / "insitu_secchi_clean.csv"


def main():
    results = pd.read_csv(RESULTS_PATH, low_memory=False)
    stations = pd.read_csv(STATIONS_PATH, low_memory=False)

    print(f"Raw results: {len(results)}")
    print(f"Raw stations: {len(stations)}")

    stations_small = stations[
        ["MonitoringLocationIdentifier", "LatitudeMeasure", "LongitudeMeasure",
         "MonitoringLocationName", "MonitoringLocationTypeName"]
    ].drop_duplicates(subset="MonitoringLocationIdentifier")

    df = results.merge(stations_small, on="MonitoringLocationIdentifier", how="inner")
    print(f"After joining to station coordinates: {len(df)}")

    # Keep only rows with a usable numeric Secchi value in meters
    df["ResultMeasureValue"] = pd.to_numeric(df["ResultMeasureValue"], errors="coerce")
    df = df[df["ResultMeasure/MeasureUnitCode"] == "m"]
    df = df.dropna(subset=["ResultMeasureValue", "LatitudeMeasure", "LongitudeMeasure", "ActivityStartDate"])
    print(f"After dropping missing/non-meter values: {len(df)}")

    # Sanity bounds: Secchi depth in a lake should realistically be 0-20 m
    df = df[(df["ResultMeasureValue"] > 0) & (df["ResultMeasureValue"] <= 20)]
    print(f"After sanity-bounding depth (0-20m): {len(df)}")

    df["ActivityStartDate"] = pd.to_datetime(df["ActivityStartDate"], errors="coerce")
    df = df.dropna(subset=["ActivityStartDate"])

    clean = pd.DataFrame({
        "site_id": df["MonitoringLocationIdentifier"],
        "site_name": df["MonitoringLocationName"],
        "state": df["StateAbbr"],
        "lat": df["LatitudeMeasure"],
        "lon": df["LongitudeMeasure"],
        "date": df["ActivityStartDate"].dt.strftime("%Y-%m-%d"),
        "secchi_m": df["ResultMeasureValue"],
    })

    # Drop exact duplicate readings (same site, date, value)
    before = len(clean)
    clean = clean.drop_duplicates(subset=["site_id", "date", "secchi_m"])
    print(f"After dropping exact duplicates: {len(clean)} (removed {before - len(clean)})")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean.to_csv(OUT_PATH, index=False)
    print(f"\nSaved {len(clean)} clean in-situ readings to {OUT_PATH}")
    print(f"Unique sites: {clean['site_id'].nunique()}")
    print(f"Date range: {clean['date'].min()} to {clean['date'].max()}")
    print(clean['state'].value_counts())


if __name__ == "__main__":
    main()
