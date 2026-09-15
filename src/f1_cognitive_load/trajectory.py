"""
Within-stint trajectory modelling of the proxy variables (addresses RQ2).

Laps are repeated measures within a driver (and, when pooling multiple
races, within a driver-race combination), so a plain OLS regression of
proxy ~ lap number would violate independence and understate uncertainty.
A linear mixed-effects model (random intercept per driver, optionally a
random slope too) is the standard way to handle this: it estimates a
population-level ("fixed effect") trend across the stint while allowing
each driver their own baseline level.

Cognitive Load Theory and attentional-narrowing models predict systematic
drift over a stint (fatigue, sustained task load); the fixed-effect slope
on lap number is the direct test of that prediction for each proxy.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

DEFAULT_FEATURES = [
    "throttle_smoothness",
    "braking_consistency",
    "sector_time_variance",
]


@dataclass
class TrajectoryResult:
    feature: str
    model: object  # fitted MixedLMResults
    params: pd.Series
    pvalues: pd.Series
    conf_int: pd.DataFrame
    n_obs: int
    n_groups: int
    converged: bool


def fit_stint_trajectory(
    feature_table: pd.DataFrame,
    feature: str,
    group_col: str = "Driver",
    lap_col: str = "LapNumber",
    quadratic: bool = False,
    random_slope: bool = False,
) -> TrajectoryResult:
    """
    Fit `feature ~ lap_col (+ lap_col^2)` with a random intercept (and
    optionally random slope) per `group_col` (default: Driver).
    """
    df = feature_table[[group_col, lap_col, feature]].dropna().copy()
    df = df.rename(columns={lap_col: "lap", feature: "y", group_col: "group"})

    df["lap_c"] = df["lap"] - df["lap"].mean()

    formula = "y ~ lap_c"
    if quadratic:
        df["lap_c2"] = df["lap_c"] ** 2
        formula += " + lap_c2"

    re_formula = "~lap_c" if random_slope else None

    model = smf.mixedlm(formula, df, groups=df["group"], re_formula=re_formula)
    result = model.fit(reml=True)

    return TrajectoryResult(
        feature=feature,
        model=result,
        params=result.params,
        pvalues=result.pvalues,
        conf_int=result.conf_int(),
        n_obs=int(result.nobs),
        n_groups=df["group"].nunique(),
        converged=result.converged,
    )


def fit_all_trajectories(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    **kwargs,
) -> dict[str, TrajectoryResult]:
    feature_cols = feature_cols or DEFAULT_FEATURES
    return {col: fit_stint_trajectory(feature_table, col, **kwargs) for col in feature_cols}


def summarize_trajectories(results: dict[str, TrajectoryResult]) -> pd.DataFrame:
    rows = []
    for feature, r in results.items():
        row = {
            "feature": feature,
            "n_obs": r.n_obs,
            "n_drivers": r.n_groups,
            "converged": r.converged,
        }
        for term in r.params.index:
            if term == "Group Var":
                continue
            row[f"{term}_coef"] = r.params[term]
            row[f"{term}_p"] = r.pvalues[term]
        rows.append(row)
    return pd.DataFrame(rows)


def predict_trajectory_curve(
    result: TrajectoryResult,
    lap_range: np.ndarray,
    lap_mean: float,
) -> np.ndarray:
    lap_c = lap_range - lap_mean
    params = result.params
    y = params.get("Intercept", 0.0) + params.get("lap_c", 0.0) * lap_c
    if "lap_c2" in params.index:
        y = y + params["lap_c2"] * (lap_c**2)
    return y

# ---------------------------------------------------------------------------
# Confound-controlled variant (H1/H2 fix)
#
# Tyre degradation and fuel burn both move (roughly) monotonically with lap
# number within a stint, exactly like any cognitive-fatigue drift would. A
# raw `feature ~ lap_number` slope from `fit_stint_trajectory` therefore
# cannot separate "driver state drifted" from "the tyre/fuel physically
# changed the car". `TyreLife` (laps completed on the current tyre set --
# itself a stint-relative, fuel-correlated lap index) and `Compound`
# (categorical) are entered as covariates below so the `lap_c` fixed effect
# estimates the within-stint trend *net of* those known physical confounds.
# ---------------------------------------------------------------------------

DEFAULT_CONFOUNDS = ["TyreLife", "Compound"]


def fit_stint_trajectory_confound_controlled(
    feature_table: pd.DataFrame,
    feature: str,
    group_col: str = "Driver",
    lap_col: str = "LapNumber",
    confound_cols: list[str] | None = None,
    quadratic: bool = False,
    random_slope: bool = False,
) -> TrajectoryResult:
    """
    Like `fit_stint_trajectory`, but adds tyre-age and tyre-compound
    covariates to the mixed model so the estimated lap-number trend is not
    confounded with tyre degradation / fuel-load effects that also scale
    with lap number. Numeric confounds (e.g. TyreLife) are mean-centered
    and entered linearly; "Compound" (if present in `confound_cols`) is
    entered as a categorical dummy (`C(Compound)`).
    """
    confound_cols = confound_cols if confound_cols is not None else DEFAULT_CONFOUNDS
    confound_cols = [c for c in confound_cols if c in feature_table.columns]

    cols = [group_col, lap_col, feature] + confound_cols
    df = feature_table[cols].dropna().copy()
    df = df.rename(columns={lap_col: "lap", feature: "y", group_col: "group"})

    df["lap_c"] = df["lap"] - df["lap"].mean()

    formula_terms = ["lap_c"]
    if quadratic:
        df["lap_c2"] = df["lap_c"] ** 2
        formula_terms.append("lap_c2")

    for col in confound_cols:
        if col == "Compound":
            df["Compound"] = df["Compound"].astype(str)
            formula_terms.append("C(Compound)")
        else:
            centered_col = f"{col}_c"
            df[centered_col] = df[col].astype(float) - df[col].astype(float).mean()
            formula_terms.append(centered_col)

    formula = "y ~ " + " + ".join(formula_terms)
    re_formula = "~lap_c" if random_slope else None

    model = smf.mixedlm(formula, df, groups=df["group"], re_formula=re_formula)
    result = model.fit(reml=True)

    return TrajectoryResult(
        feature=feature,
        model=result,
        params=result.params,
        pvalues=result.pvalues,
        conf_int=result.conf_int(),
        n_obs=int(result.nobs),
        n_groups=df["group"].nunique(),
        converged=result.converged,
    )


def fit_all_trajectories_confound_controlled(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    **kwargs,
) -> dict[str, TrajectoryResult]:
    feature_cols = feature_cols or DEFAULT_FEATURES
    return {
        col: fit_stint_trajectory_confound_controlled(feature_table, col, **kwargs)
        for col in feature_cols
    }
