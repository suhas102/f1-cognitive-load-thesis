"""
Standalone driver for Objective 4 / H4: confound-aware behavioural reports
for any driver + race, driven by a CSV of (driver, location, year) queries.

This script reproduces exactly what the "Thesis1.ipynb" Colab notebook does,
end to end, so it can be run outside Colab (your own machine, a server,
etc.) as long as you have network access to the OpenF1 API
(https://api.openf1.org) -- NOTE: OpenF1 is NOT reachable from Anthropic's
cloud sandbox that produced this package, so this has only been verified to
run inside Colab; if your machine also can't reach api.openf1.org, run it
in Colab instead (upload these files, or just use the existing notebook).

Usage
-----
    pip install -r requirements.txt
    python run_h4.py --input driver_queries.csv --output driver_reports.csv \
        --years 2023 2024 2025 --cache-dir ./data/raw

`driver_queries.csv` needs exactly 3 columns: driver,location,year
    driver   -- 3-letter code, e.g. HAM, VER, NOR (case-insensitive)
    location -- venue city (e.g. "Miami", "Suzuka") or, for a country that
                hosted only one race that season, the country name
                (e.g. "Brazil", "Japan")
    year     -- 2023, 2024, or 2025 (OpenF1 has no earlier data)

Fetching the full calendar (~70 races) takes roughly 45-75 minutes the
first time; after that, results are cached as parquet under --cache-dir and
reruns are near-instant. Race discovery, fetching, and rate-limit retries
all match the notebook's logic exactly (including the pit/race_control
404 workaround and the OpenF1 429 backoff).
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd
import requests
import yaml

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from f1_cognitive_load import config, features, modeling, report  # noqa: E402
from f1_cognitive_load.openf1_fetch import fetch_and_cache_race_openf1  # noqa: E402

OPENF1_BASE = "https://api.openf1.org/v1"
TIER2_FEATURES = ["throttle_smoothness", "braking_consistency", "sector_time_variance"]


def _slugify(name: str) -> str:
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in ascii_name)
    return re.sub(r"_+", "_", slug).strip("_")


def discover_races(years: list[int]) -> list[dict]:
    """Query OpenF1's /meetings endpoint per season and build one RaceSpec
    dict per real race weekend (pre-season testing excluded)."""
    entries = []
    for year in years:
        try:
            resp = requests.get(f"{OPENF1_BASE}/meetings", params={"year": year}, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            raise RuntimeError(
                f"OpenF1 returned HTTP {status} for /meetings?year={year}. "
                "This endpoint is documented as free/unauthenticated for historical "
                "seasons (openf1.org/docs), so a 401/403 here usually means either "
                "OpenF1's free-tier rate limit was hit (3 req/s, 30 req/min -- wait a "
                "minute and retry), a temporary OpenF1-side issue, or a network/"
                "firewall (campus Wi-Fi, VPN, antivirus SSL inspection) intercepting "
                "the request. Try opening "
                f"https://api.openf1.org/v1/meetings?year={year} directly in a "
                "browser to check which it is."
            ) from e
        for m in resp.json():
            name = str(m.get("meeting_official_name") or m.get("meeting_name") or "")
            if "test" in name.lower():
                continue
            country = m.get("country_name")
            location = m.get("location")
            if not country or not location:
                continue
            entries.append(
                {
                    "year": year,
                    "round": country,
                    "session": "R",
                    "label": f"{_slugify(location)}_{year}",
                    "location": location,
                }
            )
    entries.sort(key=lambda e: (e["year"], e["label"]))
    return entries


def build_study_config(years: list[int], config_path: Path, force_refresh: bool = False) -> "config.StudyConfig":
    # Race-weekend metadata (which races happened, where, and their labels)
    # never changes once a season is over, and a previous run already wrote
    # a complete races.yaml here. Re-querying OpenF1's /meetings endpoint on
    # every single launch is therefore both unnecessary and a needless
    # single point of failure: if OpenF1 is rate-limiting, mid-outage, or
    # otherwise unreachable, the app should still boot from the cached
    # config and cached parquet data rather than failing setup entirely.
    if not force_refresh and config_path.exists():
        try:
            cached_config = config.load_config(config_path)
            if cached_config.races:
                print(f"Using cached race list from {config_path} "
                      f"({len(cached_config.races)} races) -- skipping OpenF1 /meetings lookup")
                return cached_config
        except Exception as e:
            print(f"Cached config at {config_path} could not be loaded ({e}); re-discovering from OpenF1")

    race_entries = discover_races(years)
    if not race_entries:
        raise RuntimeError("OpenF1 returned no meetings for the requested years")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump({"races": race_entries, "drivers": {"include": []}}, sort_keys=False))
    print(f"Discovered {len(race_entries)} races across {years}")
    return config.load_config(config_path)


def fetch_all_races(study_config, raw_dir: Path) -> dict:
    import f1_cognitive_load.openf1_fetch as openf1_fetch

    openf1_fetch.RAW_DIR = raw_dir
    raw_dir.mkdir(parents=True, exist_ok=True)

    race_data = {}
    failed = []
    for i, race_spec in enumerate(study_config.races, 1):
        try:
            race_data[race_spec.label] = fetch_and_cache_race_openf1(race_spec)
        except Exception as e:
            print(f"[{race_spec.label}] SKIPPED ({e})")
            failed.append((race_spec.label, str(e)))
        if i % 10 == 0 or i == len(study_config.races):
            print(f"--- progress: {i}/{len(study_config.races)} races processed, "
                  f"{len(race_data)} ok, {len(failed)} skipped ---")
    print(f"\ndone fetching races: {len(race_data)} ok, {len(failed)} skipped")
    if failed:
        print("Skipped races:")
        for label, reason in failed:
            print(" ", label, "-", reason)
    return race_data


def build_pooled_feature_table(race_data: dict) -> pd.DataFrame:
    feature_tables = {}
    for label, (laps_df, telemetry_df, track_status_df) in race_data.items():
        ft = features.build_feature_table(telemetry_df, laps_df, track_status_df)
        ft["race_label"] = label
        feature_tables[label] = ft
        print(f"[{label}] feature table: {ft.shape[0]} laps x {ft.shape[1]} cols")
    pooled = pd.concat(feature_tables.values(), ignore_index=True)
    print("pooled feature table:", pooled.shape)
    return pooled


def fit_best_model(pooled_feature_table: pd.DataFrame):
    clf_data = modeling.prepare_classification_data(
        pooled_feature_table, feature_cols=TIER2_FEATURES, target="high_pressure", group_col="Driver"
    )
    print(f"classification data: {clf_data.X.shape[0]} laps, {clf_data.X.shape[1]} features, "
          f"{len(set(clf_data.groups))} drivers, {clf_data.y.mean():.1%} positive rate")

    logreg_result = modeling.fit_logistic_regression(clf_data)
    rf_result = modeling.fit_random_forest(clf_data)
    xgb_result = modeling.fit_xgboost(clf_data)

    comparison = modeling.compare_models([logreg_result, rf_result, xgb_result])
    print("\nDriver-grouped 5-fold CV comparison:")
    print(comparison)

    best_result = max([logreg_result, rf_result, xgb_result], key=lambda r: r.mean_metrics["roc_auc"])
    print(f"\nBest model by CV ROC-AUC: {best_result.name} ({best_result.mean_metrics['roc_auc']:.3f})")
    return best_result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="CSV with columns driver,location,year")
    parser.add_argument("--output", default="driver_reports.csv", help="Where to write the reports CSV")
    parser.add_argument("--years", nargs="+", type=int, default=[2023, 2024, 2025])
    parser.add_argument("--cache-dir", default="./data/raw", help="Where fetched race parquet files are cached")
    parser.add_argument("--config-path", default="./config/races.yaml")
    args = parser.parse_args()

    study_config = build_study_config(args.years, Path(args.config_path))
    race_data = fetch_all_races(study_config, Path(args.cache_dir))
    if not race_data:
        raise SystemExit("No races were fetched successfully -- nothing to report on.")

    pooled_feature_table = build_pooled_feature_table(race_data)
    best_result = fit_best_model(pooled_feature_table)

    report_tool = report.BehaviouralLoadReportTool(
        best_result,
        feature_table=pooled_feature_table,
        feature_cols=TIER2_FEATURES,
        race_label_col="race_label",
    )
    race_lookup = report.build_race_lookup(study_config)

    print("\nKnown (location, year) -> race_label combinations:")
    for k, v in race_lookup.items():
        print(" ", k, "->", v)

    batch_results = report_tool.batch_report_from_csv(args.input, race_lookup, output_csv_path=args.output)
    print(f"\nInput CSV:  {args.input}")
    print(f"Output CSV: {args.output}\n")
    print(batch_results[[
        "driver", "location", "year", "race_label", "resolved_driver",
        "mean_predicted_load", "pct_laps_high_load", "error",
    ]])

    for _, r in batch_results.iterrows():
        if r["error"]:
            print(f"\n[{r['driver']} / {r['location']} {r['year']}] could not generate report: {r['error']}")
        else:
            print("\n" + r["report_text"])


if __name__ == "__main__":
    main()
