"""
Rerun of Step 5 at multiple named monitoring sites across Squam and Little
Squam, instead of one central point per lake. Same harmonization/cloud-
masking/ice-exclusion pipeline as 04_match_landsat.py / 07_predict_squam.py.
Uses the Squam-excluded ("heldout") model, since that's the only model
that has genuinely never seen data from these lakes.

Resumable in site-year chunks.

Output: output/squam_predicted_secchi_multipoint.csv
"""
import argparse
import json
import time
from itertools import combinations
from pathlib import Path

import ee
import joblib
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
SITES_PATH = PROJECT_DIR / "data" / "raw" / "squam_multipoint_coordinates.csv"
MODEL_PATH = PROJECT_DIR / "data" / "processed" / "rf_model_heldout.joblib"
RAW_OUT_PATH = PROJECT_DIR / "data" / "processed" / "squam_multipoint_landsat_extracted.csv"
CHECKPOINT_PATH = PROJECT_DIR / "data" / "processed" / "squam_multipoint_checkpoint.json"
FINAL_OUT_CSV = PROJECT_DIR / "output" / "squam_predicted_secchi_multipoint.csv"
FINAL_OUT_XLSX = PROJECT_DIR / "output" / "squam_predicted_secchi_multipoint.xlsx"
EE_PROJECT = "squam-water-clarity-071026"

BUFFER_M = 45
ICE_MONTHS = {12, 1, 2, 3}
MIN_VALID_PIXELS = 5

BAND_MAP = {
    "TM_ETM": {"SR_B1": "blue", "SR_B2": "green", "SR_B3": "red",
               "SR_B4": "nir", "SR_B5": "swir1", "SR_B7": "swir2"},
    "OLI": {"SR_B2": "blue", "SR_B3": "green", "SR_B4": "red",
            "SR_B5": "nir", "SR_B6": "swir1", "SR_B7": "swir2"},
}
HARMONIZED_BANDS = ["blue", "green", "red", "nir", "swir1", "swir2"]

OUTPUT_COLUMNS = (
    ["site", "year", "image_date", "cloud_cover_pct"]
    + [f"{b}_{stat}" for b in HARMONIZED_BANDS for stat in ["median", "min", "stdDev", "count"]]
)


def mask_and_scale(image, band_map):
    qa = image.select("QA_PIXEL")
    mask = (
        qa.bitwiseAnd(1 << 1).eq(0)
        .And(qa.bitwiseAnd(1 << 3).eq(0))
        .And(qa.bitwiseAnd(1 << 4).eq(0))
        .And(qa.bitwiseAnd(1 << 5).eq(0))
    )
    sr = image.select(list(band_map.keys())).rename(list(band_map.values()))
    sr = sr.multiply(0.0000275).add(-0.2)
    sr = sr.updateMask(mask)
    return sr.copyProperties(image, ["system:time_start", "CLOUD_COVER"])


def build_landsat_collection():
    def prep(collection_id, band_map):
        coll = ee.ImageCollection(collection_id)
        return coll.map(lambda img: mask_and_scale(img, band_map))

    tm5 = prep("LANDSAT/LT05/C02/T1_L2", BAND_MAP["TM_ETM"])
    tm4 = prep("LANDSAT/LT04/C02/T1_L2", BAND_MAP["TM_ETM"])
    etm7 = prep("LANDSAT/LE07/C02/T1_L2", BAND_MAP["TM_ETM"])
    oli8 = prep("LANDSAT/LC08/C02/T1_L2", BAND_MAP["OLI"])
    oli9 = prep("LANDSAT/LC09/C02/T1_L2", BAND_MAP["OLI"])

    merged = tm4.merge(tm5).merge(etm7).merge(oli8).merge(oli9)

    def not_ice_season(img):
        month = ee.Date(img.get("system:time_start")).get("month")
        is_ice = ee.List(list(ICE_MONTHS)).contains(month)
        return img.set("is_ice_season", is_ice)

    merged = merged.map(not_ice_season).filter(ee.Filter.eq("is_ice_season", False))
    return merged


def build_reducer():
    return (
        ee.Reducer.median()
        .combine(ee.Reducer.min(), sharedInputs=True)
        .combine(ee.Reducer.stdDev(), sharedInputs=True)
        .combine(ee.Reducer.count(), sharedInputs=True)
    )


def extract_year(site_name, lat, lon, year, landsat_coll, reducer):
    pt = ee.Geometry.Point([lon, lat])
    buf = pt.buffer(BUFFER_M)
    start = ee.Date.fromYMD(year, 1, 1)
    end = start.advance(1, "year")
    year_coll = landsat_coll.filterBounds(pt).filterDate(start, end)

    def process_image(img):
        stats = img.select(HARMONIZED_BANDS).reduceRegion(
            reducer=reducer, geometry=buf, scale=30, maxPixels=1e6
        )
        return ee.Feature(None, stats).set({
            "site": site_name,
            "year": year,
            "image_date": img.get("system:time_start"),
            "cloud_cover_pct": img.get("CLOUD_COVER"),
        })

    fc = ee.FeatureCollection(year_coll.map(process_image))
    return fc.getInfo()


def flatten_features(fc_info):
    return [feat["properties"] for feat in fc_info["features"]]


def extract_all(sites, start_year, end_year):
    ee.Initialize(project=EE_PROJECT)
    landsat_coll = build_landsat_collection()
    reducer = build_reducer()

    checkpoint = {"completed": []}
    if CHECKPOINT_PATH.exists():
        checkpoint = json.loads(CHECKPOINT_PATH.read_text())

    write_header = not RAW_OUT_PATH.exists()

    for site_name, lat, lon in sites:
        for year in range(start_year, end_year + 1):
            key = f"{site_name}|{year}"
            if key in checkpoint["completed"]:
                continue
            attempt = 0
            while True:
                try:
                    fc_info = extract_year(site_name, lat, lon, year, landsat_coll, reducer)
                    break
                except Exception as e:
                    attempt += 1
                    if attempt > 4:
                        raise
                    wait = 10 * attempt
                    print(f"  {key} error ({e}); retrying in {wait}s")
                    time.sleep(wait)

            rows = flatten_features(fc_info)
            if rows:
                chunk_out = pd.DataFrame(rows)
                for col in OUTPUT_COLUMNS:
                    if col not in chunk_out.columns:
                        chunk_out[col] = pd.NA
                chunk_out = chunk_out[OUTPUT_COLUMNS]
                chunk_out.to_csv(RAW_OUT_PATH, mode="a", header=write_header, index=False)
                write_header = False

            checkpoint["completed"].append(key)
            CHECKPOINT_PATH.write_text(json.dumps(checkpoint))
            print(f"  {key}: {len(rows)} scenes extracted")


def build_predictions():
    raw = pd.read_csv(RAW_OUT_PATH, low_memory=False)
    band_cols = [f"{b}_median" for b in HARMONIZED_BANDS]
    usable = raw.dropna(subset=band_cols).copy()
    usable["pixel_count"] = usable["blue_count"]
    before = len(usable)
    usable = usable[usable["pixel_count"] >= MIN_VALID_PIXELS]
    print(f"Dropped {before - len(usable)} passes with fewer than {MIN_VALID_PIXELS} valid pixels "
          f"(mostly cloud) out of {before}")

    EPS = 1e-6
    for b1, b2 in combinations(HARMONIZED_BANDS, 2):
        usable[f"ratio_{b1}_{b2}"] = usable[f"{b1}_median"] / (usable[f"{b2}_median"] + EPS)

    saved = joblib.load(MODEL_PATH)
    model, feature_cols = saved["model"], saved["feature_cols"]

    missing = [c for c in feature_cols if c not in usable.columns]
    if missing:
        raise RuntimeError(f"Missing feature columns for prediction: {missing}")

    X = usable[feature_cols].values
    usable["predicted_secchi_m"] = model.predict(X)

    usable["date"] = pd.to_datetime(usable["image_date"], unit="ms").dt.strftime("%Y-%m-%d")
    result = usable[["site", "date", "predicted_secchi_m", "cloud_cover_pct", "pixel_count"]].copy()
    result = result.sort_values(["site", "date"]).reset_index(drop=True)

    FINAL_OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(FINAL_OUT_CSV, index=False)
    result.to_excel(FINAL_OUT_XLSX, index=False)
    print(f"\nSaved {len(result)} predictions to:\n  {FINAL_OUT_CSV}\n  {FINAL_OUT_XLSX}")
    print(result.groupby("site").size())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-year", type=int, default=1984)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--skip-extract", action="store_true")
    args = parser.parse_args()

    sites_df = pd.read_csv(SITES_PATH)
    sites = [(row["SLA_Site_Name"], row["Latitude"], row["Longitude"]) for _, row in sites_df.iterrows()]
    print(f"Sites to process: {len(sites)}")

    if not args.skip_extract:
        extract_all(sites, args.start_year, args.end_year)
    build_predictions()
