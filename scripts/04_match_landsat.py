"""
Step 2 + Step 3: For each in-situ Secchi reading, find the nearest Landsat
Collection 2 Level 2 surface reflectance scene within +/- 3 days, apply cloud
masking, exclude likely ice-covered winter scenes (Dec-Mar, a practical
proxy for New England lake ice season), and extract per-band median/min/std
in a small window around the point, plus scene cloud cover % and valid
pixel count.

Processes in resumable chunks: progress is checkpointed to
data/processed/match_checkpoint.json and results are appended to
data/processed/matched_landsat.csv, so an interruption doesn't lose work.

Usage:
    python scripts/04_match_landsat.py [--limit N] [--chunk-size N]
"""
import argparse
import json
import time
from pathlib import Path

import ee
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[1]
IN_PATH = PROJECT_DIR / "data" / "processed" / "insitu_secchi_clean.csv"
OUT_PATH = PROJECT_DIR / "data" / "processed" / "matched_landsat.csv"
CHECKPOINT_PATH = PROJECT_DIR / "data" / "processed" / "match_checkpoint.json"
EE_PROJECT = "squam-water-clarity-071026"

MAX_DAYS = 3
BUFFER_M = 45  # ~3x3 pixel window at 30m resolution
ICE_MONTHS = {12, 1, 2, 3}  # practical proxy for New England lake ice season

BAND_MAP = {
    # Landsat 4/5 TM, Landsat 7 ETM+
    "TM_ETM": {"SR_B1": "blue", "SR_B2": "green", "SR_B3": "red",
               "SR_B4": "nir", "SR_B5": "swir1", "SR_B7": "swir2"},
    # Landsat 8/9 OLI
    "OLI": {"SR_B2": "blue", "SR_B3": "green", "SR_B4": "red",
            "SR_B5": "nir", "SR_B6": "swir1", "SR_B7": "swir2"},
}
HARMONIZED_BANDS = ["blue", "green", "red", "nir", "swir1", "swir2"]

# Fixed output column order -- every chunk is reindexed to this exact schema
# before being appended, so differing property order/presence across GEE
# responses can never silently misalign columns between chunks.
OUTPUT_COLUMNS = (
    ["row_id", "has_match", "matched_image_date", "cloud_cover_pct"]
    + [f"{b}_{stat}" for b in HARMONIZED_BANDS for stat in ["median", "min", "stdDev", "count"]]
)


def mask_and_scale(image, band_map):
    qa = image.select("QA_PIXEL")
    # bits: 1=dilated cloud, 3=cloud, 4=cloud shadow, 5=snow
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


def match_chunk(chunk_df, landsat_coll, reducer):
    features = []
    for _, row in chunk_df.iterrows():
        date_ms = int(pd.Timestamp(row["date"]).timestamp() * 1000)
        geom = ee.Geometry.Point([row["lon"], row["lat"]])
        f = ee.Feature(geom, {
            "row_id": str(row["row_id"]),
            "system:time_start": date_ms,
        })
        features.append(f)
    points_fc = ee.FeatureCollection(features)

    join_filter = ee.Filter.And(
        ee.Filter.maxDifference(
            difference=MAX_DAYS * 24 * 60 * 60 * 1000,
            leftField="system:time_start",
            rightField="system:time_start",
        ),
        ee.Filter.intersects(leftField=".geo", rightField=".geo"),
    )
    joined = ee.Join.saveAll(matchesKey="images", measureKey="dt", ordering="dt", ascending=True).apply(
        points_fc, landsat_coll, join_filter
    )

    def process_point(feature):
        images = ee.List(feature.get("images"))
        has_match = images.size().gt(0)

        def with_match():
            img = ee.Image(images.get(0))
            buf = feature.geometry().buffer(BUFFER_M)
            stats = img.select(HARMONIZED_BANDS).reduceRegion(
                reducer=reducer, geometry=buf, scale=30, maxPixels=1e6
            )
            return feature.set(stats).set({
                "matched_image_date": img.get("system:time_start"),
                "cloud_cover_pct": img.get("CLOUD_COVER"),
                "has_match": 1,
            })

        def without_match():
            return feature.set({"has_match": 0})

        return ee.Algorithms.If(has_match, with_match(), without_match())

    result_fc = ee.FeatureCollection(joined.map(process_point))
    return result_fc.getInfo()


def flatten_features(fc_info):
    rows = []
    for feat in fc_info["features"]:
        props = feat["properties"]
        rows.append(props)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--chunk-size", type=int, default=150)
    parser.add_argument("--start-date", type=str, default="1984-01-01")
    args = parser.parse_args()

    ee.Initialize(project=EE_PROJECT)

    df = pd.read_csv(IN_PATH)
    df = df[df["date"] >= args.start_date].reset_index(drop=True)
    df["row_id"] = df.index.astype(str)
    if args.limit:
        df = df.iloc[: args.limit]

    print(f"Matching {len(df)} in-situ readings (from {args.start_date} onward) against Landsat...")

    checkpoint = {"completed_chunks": []}
    if CHECKPOINT_PATH.exists():
        checkpoint = json.loads(CHECKPOINT_PATH.read_text())

    landsat_coll = build_landsat_collection()
    reducer = build_reducer()

    chunk_size = args.chunk_size
    n_chunks = (len(df) + chunk_size - 1) // chunk_size

    write_header = not OUT_PATH.exists()

    for i in range(n_chunks):
        if i in checkpoint["completed_chunks"]:
            continue
        chunk_df = df.iloc[i * chunk_size: (i + 1) * chunk_size]
        attempt = 0
        while True:
            try:
                fc_info = match_chunk(chunk_df, landsat_coll, reducer)
                break
            except Exception as e:
                attempt += 1
                if attempt > 4:
                    raise
                wait = 10 * attempt
                print(f"  chunk {i} error ({e}); retrying in {wait}s (attempt {attempt})")
                time.sleep(wait)

        rows = flatten_features(fc_info)
        chunk_out = pd.DataFrame(rows)
        for col in OUTPUT_COLUMNS:
            if col not in chunk_out.columns:
                chunk_out[col] = pd.NA
        chunk_out = chunk_out[OUTPUT_COLUMNS]
        chunk_out.to_csv(OUT_PATH, mode="a", header=write_header, index=False)
        write_header = False

        checkpoint["completed_chunks"].append(i)
        CHECKPOINT_PATH.write_text(json.dumps(checkpoint))

        matched = sum(1 for r in rows if r.get("has_match") == 1)
        print(f"  chunk {i+1}/{n_chunks}: {len(rows)} points, {matched} matched to a Landsat scene")

    print(f"\nDone. Results in {OUT_PATH}")


if __name__ == "__main__":
    main()
