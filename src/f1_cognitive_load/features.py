"""
Behavioural proxy feature engineering.

Each function below computes one of the telemetry-derived proxy variables
named in the research questions, grounded in the theoretical framework:

- Control input derivatives (throttle/brake/steering rate & jerk) follow
  Castignani et al. (2015) and Ventura et al. (2021), who show that first-
  and second-derivative features of control inputs carry more information
  about driver state than raw input levels.
- Throttle smoothness / braking consistency operationalise Cognitive Load
  Theory (Sweller, 1988): as aggregate cognitive demand rises relative to
  available working-memory resources, fine motor control degrades and
  control-input variability increases.
- Sector time variance operationalises both Cognitive Load Theory and
  attentional narrowing (Starcke & Brand, 2012; Endsley, 1995): inconsistent
  pace within a stint is a downstream signature of fluctuating attentional
  and cognitive state.

All functions are pure (input DataFrame -> output DataFrame) and have no
network dependency, so they can be unit-tested with synthetic telemetry.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GROUP_KEYS = ["Driver", "LapNumber"]


def _diff_over_time(series: pd.Series, time_seconds: pd.Series) -> pd.Series:
    """First derivative of `series` w.r.t. time, with divide-by-zero guarded."""
    dt = time_seconds.diff()
    dt = dt.replace(0, np.nan)
    return series.diff() / dt


def add_control_derivatives(telemetry: pd.DataFrame) -> pd.DataFrame:
    """
    Add first-derivative (rate) and second-derivative (jerk) columns for
    Throttle, Brake, and Steering (Steering only if present), computed per
    (Driver, LapNumber) group and ordered by time within the lap.

    Expects `telemetry` to have: Driver, LapNumber, Time (timedelta or
    seconds), Throttle (0-100), Brake (0/1 or 0-100), and optionally
    Steering / RPM / Speed. Matches the schema produced by
    `data_acquisition.extract_telemetry`.
    """
    df = telemetry.copy()

    if pd.api.types.is_timedelta64_dtype(df["Time"]):
        df["_t_sec"] = df["Time"].dt.total_seconds()
    else:
        df["_t_sec"] = df["Time"].astype(float)

    df = df.sort_values(GROUP_KEYS + ["_t_sec"])

    input_cols = [c for c in ["Throttle", "Brake", "Steering"] if c in df.columns]

    for col in input_cols:
        rate_col = f"{col}_rate"
        jerk_col = f"{col}_jerk"
        df[rate_col] = df.groupby(GROUP_KEYS, group_keys=False).apply(
            lambda g: _diff_over_time(g[col].astype(float), g["_t_sec"]), include_groups=False
        ).reset_index(drop=True).values
        df[jerk_col] = df.groupby(GROUP_KEYS, group_keys=False).apply(
            lambda g: _diff_over_time(g[rate_col], g["_t_sec"]), include_groups=False
        ).reset_index(drop=True).values

    return df.drop(columns=["_t_sec"])


def compute_throttle_smoothness(telemetry_with_derivatives: pd.DataFrame) -> pd.DataFrame:
    """
    Per-lap throttle smoothness score = -std(throttle_rate). Higher (closer
    to 0) means smoother, more automatic (System 1) throttle application;
    more negative means erratic, effortful (System 2-heavy) modulation.
    """
    df = telemetry_with_derivatives
    agg = (
        df.groupby(GROUP_KEYS)["Throttle_rate"]
        .agg(throttle_rate_std="std", throttle_jerk_mean=lambda s: s.abs().mean())
        .reset_index()
    )
    agg["throttle_smoothness"] = -agg["throttle_rate_std"]
    return agg


def compute_braking_consistency(telemetry: pd.DataFrame, brake_threshold: float = 0.5) -> pd.DataFrame:
    """
    For each (Driver, Stint), find the brake-onset distance (the `Distance`
    at which Brake first crosses `brake_threshold`) for every lap in the
    stint, then compute the standard deviation of that onset distance
    across laps. A low std means the driver brakes at a highly repeatable
    point lap after lap (automatic, low-load); a high std means brake
    points are drifting, consistent with degraded attentional consistency
    under load (Starcke & Brand, 2012).

    Expects telemetry to include Distance, Brake, Driver, LapNumber, Stint.
    """
    df = telemetry.copy()
    df["_braking"] = df["Brake"].astype(float) >= brake_threshold

    onset_rows = []
    for (drv, lap), g in df.groupby(["Driver", "LapNumber"]):
        g = g.sort_values("Distance")
        braking = g[g["_braking"]]
        if braking.empty:
            continue
        onset_distance = braking["Distance"].iloc[0]
        stint = g["Stint"].iloc[0] if "Stint" in g.columns else None
        onset_rows.append({"Driver": drv, "LapNumber": lap, "Stint": stint, "brake_onset_distance": onset_distance})

    onsets = pd.DataFrame(onset_rows)
    if onsets.empty:
        return onsets

    consistency = (
        onsets.groupby(["Driver", "Stint"])["brake_onset_distance"]
        .std()
        .reset_index(name="brake_onset_std")
    )
    consistency["braking_consistency"] = -consistency["brake_onset_std"]
    return onsets.merge(consistency, on=["Driver", "Stint"], how="left")


def compute_sector_variance(
    laps: pd.DataFrame,
    window: int = 5,
    group_cols: tuple[str, ...] = ("Driver",),
) -> pd.DataFrame:
    """
    Rolling within-stint variance of each sector time, computed over a
    trailing window of `window` laps within each group.

    `group_cols` defaults to ("Driver",), which is correct for a single
    race weekend (FastF1's `session.laps` schema). When pooling laps from
    multiple race weekends/seasons in one table, pass e.g.
    `("Season", "GP", "Driver")` so the rolling window doesn't leak across
    different races for the same driver.

    Sector time columns may be either pandas timedeltas (FastF1's native
    schema) or plain floats in seconds (as in locally-supplied CSV exports)
    — both are handled automatically.
    """
    df = laps.copy().sort_values(list(group_cols) + ["LapNumber"])
    sector_cols = [c for c in ["Sector1Time", "Sector2Time", "Sector3Time"] if c in df.columns]

    for col in sector_cols:
        seconds_col = f"{col}_s"
        if pd.api.types.is_timedelta64_dtype(df[col]):
            df[seconds_col] = df[col].dt.total_seconds()
        else:
            df[seconds_col] = df[col].astype(float)
        var_col = f"{col}_rolling_var"
        df[var_col] = (
            df.groupby(list(group_cols))[seconds_col]
            .rolling(window=window, min_periods=max(2, window // 2))
            .var()
            .reset_index(level=list(range(len(group_cols))), drop=True)
        )

    variance_cols = [f"{c}_rolling_var" for c in sector_cols]
    df["sector_time_variance"] = df[variance_cols].mean(axis=1)
    return df


def flag_high_pressure_windows(
    laps: pd.DataFrame,
    track_status: pd.DataFrame,
    position_delta_threshold: int = 1,
) -> pd.DataFrame:
    """
    Label each lap as a high-pressure moment or baseline driving.

    High-pressure = any of:
      - TrackStatus indicates Safety Car / VSC / Red Flag active or just
        ended within the lap (restart window) — codes per FastF1 docs:
        '1' Track clear, '2' Yellow, '4' Safety Car, '5' Red Flag, '6'/'7' VSC.
      - Position changed by >= `position_delta_threshold` vs. the previous
        lap (overtake made or lost).
      - PitOutTime / PitInTime present (in/out lap — undercut/overcut window).

    Everything else is baseline driving, used as the comparison condition
    for the research questions on high-pressure behavioural signatures.
    """
    df = laps.copy().sort_values(["Driver", "LapNumber"])

    pressure_codes = {"2", "4", "5", "6", "7"}
    if "TrackStatus" in df.columns:
        df["_track_status_pressure"] = df["TrackStatus"].astype(str).apply(
            lambda s: any(code in pressure_codes for code in s)
        )
    else:
        df["_track_status_pressure"] = False

    if "Position" in df.columns:
        df["_position_delta"] = df.groupby("Driver")["Position"].diff().abs()
        df["_position_pressure"] = df["_position_delta"] >= position_delta_threshold
    else:
        df["_position_pressure"] = False

    pit_cols = [c for c in ["PitInTime", "PitOutTime"] if c in df.columns]
    if pit_cols:
        df["_pit_pressure"] = df[pit_cols].notna().any(axis=1)
    else:
        df["_pit_pressure"] = False

    df["high_pressure"] = df["_track_status_pressure"] | df["_position_pressure"] | df["_pit_pressure"]

    # keep the sub-flags (renamed, no leading underscore) rather than dropping
    # them -- high_pressure lumps together three qualitatively different
    # situations (a cautious safety-car restart vs. a demanding overtake vs.
    # a pit in/out lap), and RQ1's validity analysis needs to be able to
    # tell them apart rather than only seeing the OR of all three.
    df = df.rename(
        columns={
            "_track_status_pressure": "track_status_pressure",
            "_position_pressure": "position_pressure",
            "_pit_pressure": "pit_pressure",
        }
    )
    return df


def build_feature_table(
    telemetry: pd.DataFrame,
    laps: pd.DataFrame,
    track_status: pd.DataFrame,
) -> pd.DataFrame:
    """Convenience wrapper: run the full feature pipeline and merge to one lap-level table."""
    telemetry_d = add_control_derivatives(telemetry)
    throttle = compute_throttle_smoothness(telemetry_d)
    braking = compute_braking_consistency(telemetry_d)
    laps_var = compute_sector_variance(laps)
    laps_flagged = flag_high_pressure_windows(laps_var, track_status)

    out = laps_flagged.merge(throttle, on=GROUP_KEYS, how="left")
    if not braking.empty:
        braking_lap = braking[["Driver", "LapNumber", "braking_consistency"]].drop_duplicates()
        out = out.merge(braking_lap, on=GROUP_KEYS, how="left")
    return out
