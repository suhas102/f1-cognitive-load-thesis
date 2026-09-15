import requests
import pandas as pd
import numpy as np
from pathlib import Path

# --- Data-source pivot -----------------------------------------------------
# FastF1's primary source (livetiming.formula1.com) and even its community
# fallback mirror (livetiming-mirror.fastf1.dev) return
# `SessionNotAvailableError: No data for this session` for every endpoint
# when called from this Colab VM's IP range -- confirmed identically for
# both the 2023 Singapore and Japan races, so it is not session-specific
# data corruption. A real Chrome tab loading the exact same
# livetiming.formula1.com JSON URL succeeds, so this is very likely
# TLS/HTTP-fingerprint-level bot mitigation (Cloudflare/Akamai), which a
# plain User-Agent header spoof on `requests` cannot get past.
# OpenF1 (api.openf1.org), a modern, actively maintained, free F1 data API,
# IS reachable from this VM (verified: HTTP 200 with real session data), so
# the fetch-and-cache pipeline below sources from OpenF1 instead and
# reshapes its data into the same laps / telemetry / track_status schema
# `features.py`/`trajectory.py`/`validity.py`/`modeling.py` already expect.
# One adaptation: OpenF1's car telemetry has no cumulative `Distance`
# column (unlike FastF1), so it is reconstructed here by integrating speed
# over time within each lap -- an approximation, but preserves the
# brake-onset-distance logic in `compute_braking_consistency` unchanged.
# ----------------------------------------------------------------------------

OPENF1_BASE = "https://api.openf1.org/v1"


import time

def _openf1_get(endpoint, **params):
    # OpenF1's free tier rate-limits aggressively (HTTP 429) once a session
    # makes many requests in a short window -- expected here since fetching
    # the full 2023-2025 calendar issues thousands of calls. Retry with
    # exponential backoff (honouring Retry-After when OpenF1 sends one)
    # rather than letting a single 429 kill the whole race's fetch.
    max_retries = 6
    for attempt in range(max_retries):
        r = requests.get(f"{OPENF1_BASE}/{endpoint}", params=params, timeout=30)
        if r.status_code == 429:
            retry_after = r.headers.get("Retry-After")
            wait = float(retry_after) if retry_after else min(60, 2 ** attempt * 3)
            if attempt < max_retries - 1:
                time.sleep(wait)
                continue
        r.raise_for_status()
        return pd.DataFrame(r.json())
    r.raise_for_status()
    return pd.DataFrame(r.json())


def _find_session_key(year, round_name, session_type, location=None):
    sessions = _openf1_get("sessions", year=year, country_name=round_name)
    if sessions.empty:
        raise ValueError(f"No OpenF1 sessions found for {year} {round_name}")
    if location:
        located = sessions[sessions["location"].astype(str).str.lower() == str(location).lower()]
        if located.empty:
            raise ValueError(
                f"No OpenF1 sessions found for {year} {round_name} at location={location!r}"
            )
        sessions = located
    type_map = {"R": "Race", "Q": "Qualifying", "FP1": "Practice 1",
                "FP2": "Practice 2", "FP3": "Practice 3", "S": "Sprint"}
    want = type_map.get(session_type, session_type)
    match = sessions[sessions["session_name"] == want]
    if match.empty:
        raise ValueError(f"No OpenF1 session named {want!r} for {year} {round_name}")
    if len(match) > 1:
        # Happens when `round_name` (country) hosted more than one Grand
        # Prix that year (e.g. USA: Miami/Austin/Las Vegas) and no
        # `location` was given to disambiguate -- picking arbitrarily here
        # would silently fetch the wrong race, so fail loudly instead.
        candidates = match[["location", "circuit_short_name", "date_start"]].to_dict("records")
        raise ValueError(
            f"Multiple OpenF1 {want!r} sessions found for {year} {round_name} -- "
            f"pass `location` on the RaceSpec to disambiguate. Candidates: {candidates}"
        )
    return int(match.iloc[0]["session_key"])


def fetch_and_cache_race_openf1(race_spec, force=False):
    """
    OpenF1-backed replacement for fetch_and_cache_race with the same
    contract: returns (laps_df, telemetry_df, track_status_df) and caches
    them as parquet under data/raw/<label>/, idempotently.
    """
    out_dir = RAW_DIR / race_spec.label
    out_dir.mkdir(parents=True, exist_ok=True)
    laps_path = out_dir / "laps.parquet"
    tel_path = out_dir / "telemetry.parquet"
    ts_path = out_dir / "track_status.parquet"

    if not force and laps_path.exists() and tel_path.exists() and ts_path.exists():
        print(f"[{race_spec.label}] cached parquet found, loading from disk")
        return (
            pd.read_parquet(laps_path),
            pd.read_parquet(tel_path),
            pd.read_parquet(ts_path),
        )

    print(f"[{race_spec.label}] fetching {race_spec.year} {race_spec.round} {race_spec.session} from OpenF1...")
    session_key = _find_session_key(
        race_spec.year, race_spec.round, race_spec.session,
        location=getattr(race_spec, "location", None),
    )

    drivers = _openf1_get("drivers", session_key=session_key)
    num_to_code = dict(zip(drivers["driver_number"], drivers["name_acronym"]))

    laps_raw = _openf1_get("laps", session_key=session_key)
    stints = _openf1_get("stints", session_key=session_key)
    # `pit`, `race_control` and `position` are all optional enrichments
    # (pit-stop flags, track-status/flag timeline, live position) -- OpenF1
    # returns a 404 for some sessions (observed on several early-2023
    # races) even though `laps`/`stints`/`drivers` for that same session
    # are fine, so a missing one of these should degrade gracefully rather
    # than losing the whole race.
    try:
        pit = _openf1_get("pit", session_key=session_key)
    except Exception:
        pit = pd.DataFrame()
    try:
        race_control = _openf1_get("race_control", session_key=session_key)
    except Exception:
        race_control = pd.DataFrame()
    try:
        position = _openf1_get("position", session_key=session_key)
    except Exception:
        position = pd.DataFrame()

    laps_raw = laps_raw.dropna(subset=["lap_number", "driver_number"]).copy()
    laps_raw["Driver"] = laps_raw["driver_number"].map(num_to_code)
    laps_raw["LapNumber"] = laps_raw["lap_number"].astype(float)
    laps_raw["Sector1Time"] = laps_raw.get("duration_sector_1")
    laps_raw["Sector2Time"] = laps_raw.get("duration_sector_2")
    laps_raw["Sector3Time"] = laps_raw.get("duration_sector_3")
    laps_raw["LapTime"] = laps_raw.get("lap_duration")
    laps_raw["date_start"] = pd.to_datetime(laps_raw["date_start"], utc=True, errors="coerce")

    tyre_rows = []
    for _, s in stints.iterrows():
        drv = num_to_code.get(s["driver_number"])
        if drv is None or pd.isna(s.get("lap_start")) or pd.isna(s.get("lap_end")):
            continue
        for lap_n in range(int(s["lap_start"]), int(s["lap_end"]) + 1):
            tyre_rows.append({
                "Driver": drv,
                "LapNumber": float(lap_n),
                "Compound": s.get("compound"),
                "Stint": s.get("stint_number"),
                "TyreLife": float(s.get("tyre_age_at_start") or 0) + (lap_n - int(s["lap_start"])),
            })
    tyre_df = pd.DataFrame(tyre_rows)
    laps = laps_raw.merge(tyre_df, on=["Driver", "LapNumber"], how="left") if not tyre_df.empty else laps_raw.copy()

    pit_laps = set()
    if not pit.empty:
        pit_laps = set(zip(pit["driver_number"].map(num_to_code), pit["lap_number"].astype(float)))
    laps["PitInTime"] = laps.apply(lambda r: 1.0 if (r["Driver"], r["LapNumber"]) in pit_laps else np.nan, axis=1)
    laps["PitOutTime"] = laps["is_pit_out_lap"].map({True: 1.0, False: np.nan}) if "is_pit_out_lap" in laps.columns else np.nan

    laps["Position"] = np.nan
    if not position.empty and "date" in position.columns:
        position = position.dropna(subset=["driver_number", "date", "position"]).copy()
        position["Driver"] = position["driver_number"].map(num_to_code)
        position["date"] = pd.to_datetime(position["date"], utc=True, errors="coerce")
        pos_frames = []
        for drv, grp in laps.dropna(subset=["date_start"]).groupby("Driver"):
            pdrv = position[position["Driver"] == drv].sort_values("date")
            if pdrv.empty:
                continue
            merged = pd.merge_asof(
                grp.sort_values("date_start"),
                pdrv[["date", "position"]].rename(columns={"date": "date_start"}),
                on="date_start", direction="backward",
            )
            pos_frames.append(merged[["Driver", "LapNumber", "position"]])
        if pos_frames:
            pos_lookup = pd.concat(pos_frames, ignore_index=True).rename(columns={"position": "Position_"})
            laps = laps.drop(columns=["Position"]).merge(pos_lookup, on=["Driver", "LapNumber"], how="left")
            laps = laps.rename(columns={"Position_": "Position"})

    pressure_flags = {"YELLOW", "DOUBLE YELLOW", "SAFETY CAR", "RED"}
    status_code = {"YELLOW": "2", "DOUBLE YELLOW": "2", "SAFETY CAR": "4", "RED": "5"}
    laps["TrackStatus"] = "1"
    if not race_control.empty and "date" in race_control.columns:
        rc = race_control.dropna(subset=["date"]).copy()
        rc["date"] = pd.to_datetime(rc["date"], utc=True, errors="coerce")
        events = []
        for _, row in rc.sort_values("date").iterrows():
            flag = str(row.get("flag") or "").upper()
            if flag in pressure_flags:
                events.append((row["date"], status_code.get(flag, "2")))
            elif flag in {"CLEAR", "GREEN"}:
                events.append((row["date"], "1"))
        if events:
            ev_df = pd.DataFrame(events, columns=["date", "code"]).sort_values("date")
            for drv, grp in laps.dropna(subset=["date_start"]).groupby("Driver"):
                merged = pd.merge_asof(
                    grp[["date_start"]].sort_values("date_start"),
                    ev_df.rename(columns={"date": "date_start"}),
                    on="date_start", direction="backward",
                )
                laps.loc[merged.index, "TrackStatus"] = merged["code"].fillna("1").values

    track_status = (
        race_control.rename(columns={"date": "Time", "message": "Message", "flag": "Status"})
        if not race_control.empty else pd.DataFrame(columns=["Time", "Status", "Message"])
    )

    stint_lookup = {}
    if "Stint" in laps.columns:
        stint_lookup = {
            (r.Driver, r.LapNumber): r.Stint
            for r in laps[["Driver", "LapNumber", "Stint"]].dropna(subset=["Stint"]).itertuples()
        }

    telemetry_frames = []
    n_ok, n_fail = 0, 0
    lap_windows = laps.dropna(subset=["date_start"]).sort_values(["Driver", "LapNumber"])
    for drv in laps["Driver"].dropna().unique():
        drv_num_series = drivers.loc[drivers["name_acronym"] == drv, "driver_number"]
        if drv_num_series.empty:
            continue
        drv_num = int(drv_num_series.iloc[0])
        try:
            car = _openf1_get("car_data", session_key=session_key, driver_number=drv_num)
        except Exception:
            n_fail += 1
            continue
        if car.empty or "date" not in car.columns:
            n_fail += 1
            continue
        car["date"] = pd.to_datetime(car["date"], utc=True, errors="coerce")
        car = car.dropna(subset=["date"]).sort_values("date")

        drv_laps = lap_windows[lap_windows["Driver"] == drv].reset_index(drop=True)
        starts = drv_laps["date_start"].tolist()
        lap_nums = drv_laps["LapNumber"].tolist()
        for i, (start, lap_n) in enumerate(zip(starts, lap_nums)):
            end = starts[i + 1] if i + 1 < len(starts) else start + pd.Timedelta(minutes=3)
            chunk = car[(car["date"] >= start) & (car["date"] < end)].copy()
            if chunk.empty:
                n_fail += 1
                continue
            chunk["_t_sec"] = (chunk["date"] - chunk["date"].iloc[0]).dt.total_seconds()
            dt = chunk["_t_sec"].diff().fillna(0.0)
            speed_ms = chunk.get("speed", pd.Series(0, index=chunk.index)).astype(float) / 3.6
            chunk["Distance"] = (speed_ms * dt).cumsum()
            chunk["Time"] = chunk["_t_sec"]
            chunk["Throttle"] = chunk.get("throttle", np.nan)
            chunk["Brake"] = chunk.get("brake", np.nan)
            chunk["Driver"] = drv
            chunk["LapNumber"] = lap_n
            chunk["Stint"] = stint_lookup.get((drv, lap_n))
            telemetry_frames.append(chunk[["Driver", "LapNumber", "Stint", "Time", "Distance", "Throttle", "Brake"]])
            n_ok += 1

    telemetry = pd.concat(telemetry_frames, ignore_index=True) if telemetry_frames else pd.DataFrame()

    laps = laps.drop(columns=["date_start"], errors="ignore")
    laps.to_parquet(laps_path)
    telemetry.to_parquet(tel_path)
    track_status.to_parquet(ts_path)
    print(f"[{race_spec.label}] saved: {len(laps)} laps ({n_ok} telemetry laps ok, {n_fail} failed), "
          f"{len(telemetry)} telemetry rows, {len(track_status)} track-status rows")
    return laps, telemetry, track_status
