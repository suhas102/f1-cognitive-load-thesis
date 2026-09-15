"""
Construct-validity analysis for the three telemetry-derived proxy variables
(addresses RQ1: can throttle_smoothness, braking_consistency, and
sector_time_variance serve as valid proxies for cognitive load /
attentional state?).

Three complementary angles, standard for justifying a novel behavioural
proxy in the absence of a ground-truth cognitive-load measurement:

1. Convergent validity (do the proxies move together the way a shared
   underlying construct predicts?) via a correlation matrix and PCA. Note
   throttle_smoothness and braking_consistency are defined as *negative*
   deviation measures (higher = smoother/more consistent), while
   sector_time_variance is a raw variance (higher = less consistent), so a
   coherent single "cognitive load" factor should load these with opposite
   sign -- `align_signs=True` flips sector_time_variance for the PCA/
   correlation-summary steps so all three point the same direction
   (higher = more load) before combining.

2. Known-groups validity (do the proxies actually differ between
   high-pressure and baseline laps, as they should if they track load)
   via a Mann-Whitney U test per proxy, with a rank-biserial effect size.

3. Internal consistency of the resulting composite (Cronbach's alpha on
   the sign-aligned proxies) as a rough single-number summary of how much
   they're measuring "the same thing".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu, pearsonr, spearmanr
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

DEFAULT_FEATURES = [
    "throttle_smoothness",
    "braking_consistency",
    "sector_time_variance",
]

# proxies where a HIGHER raw value means LOWER inferred cognitive load;
# these get sign-flipped when we need everything pointing the same way
_INVERTED_FEATURES = {"throttle_smoothness", "braking_consistency"}


def _aligned(df: pd.DataFrame, feature_cols: list[str]) -> pd.DataFrame:
    """Return a copy where every column points 'higher = more inferred load'."""
    out = df[feature_cols].copy()
    for col in feature_cols:
        if col in _INVERTED_FEATURES:
            out[col] = -out[col]
    return out


def correlation_matrix(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    method: str = "pearson",
) -> pd.DataFrame:
    """
    Pairwise correlation (and p-value) between every pair of proxies, in
    their RAW (not sign-aligned) direction -- so a coherent construct shows
    up as throttle_smoothness/braking_consistency correlating *negatively*
    with sector_time_variance, not positively.
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    clean = feature_table[feature_cols].dropna()
    corr_fn = pearsonr if method == "pearson" else spearmanr

    rows = []
    for i, a in enumerate(feature_cols):
        for b in feature_cols[i + 1 :]:
            r, p = corr_fn(clean[a], clean[b])
            rows.append({"feature_a": a, "feature_b": b, "r": r, "p": p, "n": len(clean)})
    return pd.DataFrame(rows)


@dataclass
class PCAResult:
    explained_variance_ratio: np.ndarray
    loadings: pd.DataFrame
    scores: np.ndarray
    n_obs: int


def run_pca(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    align_signs: bool = True,
) -> PCAResult:
    """
    PCA on the standardized proxies. If a single latent "cognitive load"
    factor drives all three, PC1 should explain a large majority of the
    variance and load all three features with the same sign (after
    align_signs flips the inverted ones).
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    clean = feature_table[feature_cols].dropna()
    X = _aligned(clean, feature_cols) if align_signs else clean[feature_cols]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    pca = PCA(n_components=len(feature_cols))
    scores = pca.fit_transform(X_scaled)

    loadings = pd.DataFrame(
        pca.components_.T,
        index=feature_cols,
        columns=[f"PC{i + 1}" for i in range(len(feature_cols))],
    )

    return PCAResult(
        explained_variance_ratio=pca.explained_variance_ratio_,
        loadings=loadings,
        scores=scores,
        n_obs=len(clean),
    )


def known_groups_validity(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    group_col: str = "high_pressure",
) -> pd.DataFrame:
    """
    Mann-Whitney U test per proxy: does its distribution actually differ
    between high-pressure and baseline laps? A valid cognitive-load proxy
    should show a significant difference, in the direction consistent with
    higher inferred load under pressure (raw value LOWER for
    throttle_smoothness/braking_consistency, HIGHER for
    sector_time_variance, under high_pressure==True).

    Effect size is the rank-biserial correlation (2*AUC - 1): 0 = no
    separation, +-1 = complete separation. Its sign follows the raw
    (not sign-aligned) feature direction.
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    rows = []
    for col in feature_cols:
        clean = feature_table[[col, group_col]].dropna()
        pos = clean.loc[clean[group_col].astype(bool), col]
        neg = clean.loc[~clean[group_col].astype(bool), col]

        if len(pos) < 2 or len(neg) < 2:
            rows.append(
                {
                    "feature": col,
                    "n_high_pressure": len(pos),
                    "n_baseline": len(neg),
                    "U": float("nan"),
                    "p": float("nan"),
                    "rank_biserial": float("nan"),
                    "median_high_pressure": pos.median() if len(pos) else float("nan"),
                    "median_baseline": neg.median() if len(neg) else float("nan"),
                }
            )
            continue

        # method="asymptotic" is forced explicitly (rather than the default
        # "auto") because scipy's "auto" heuristic can select the exact
        # permutation method for some tie/size combinations, whose cost is
        # ~O(n1*n2) -- fine for a handful of races but catastrophically slow
        # (and memory-hungry) once n1/n2 are in the tens of thousands, as
        # they are once pooled across the full 2023-2025 calendar. The
        # normal approximation is standard practice at this sample size.
        U, p = mannwhitneyu(pos, neg, alternative="two-sided", method="asymptotic")
        # rank-biserial correlation from the U statistic
        rank_biserial = 2 * (U / (len(pos) * len(neg))) - 1

        rows.append(
            {
                "feature": col,
                "n_high_pressure": len(pos),
                "n_baseline": len(neg),
                "U": U,
                "p": p,
                "rank_biserial": rank_biserial,
                "median_high_pressure": pos.median(),
                "median_baseline": neg.median(),
            }
        )
    return pd.DataFrame(rows)


def known_groups_validity_by_subtype(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    subtype_cols: tuple[str, ...] = ("track_status_pressure", "position_pressure", "pit_pressure"),
) -> pd.DataFrame:
    """
    Like known_groups_validity, but splits `high_pressure` back into its
    three qualitatively different sub-types (safety-car/VSC, position
    change, pit in/out -- see features.flag_high_pressure_windows) and
    tests each separately against a *pure* baseline (laps flagged under
    none of the three sub-types).

    This exists because `high_pressure` is an OR of three fairly different
    situations -- a cautious safety-car restart plausibly produces smoother
    inputs, while a wheel-to-wheel overtake plausibly produces rougher
    ones -- so a single pooled high_pressure comparison can mask or even
    reverse a proxy's real effect. Requires feature_table to include the
    three sub-flag columns (present in features.build_feature_table's
    output).
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    missing = [c for c in subtype_cols if c not in feature_table.columns]
    if missing:
        raise ValueError(
            f"feature_table is missing sub-type columns {missing} -- "
            "rebuild it with the current features.flag_high_pressure_windows"
        )

    pure_baseline = ~feature_table[list(subtype_cols)].any(axis=1)

    rows = []
    for subtype in subtype_cols:
        pure_subtype = feature_table[subtype] & ~(
            feature_table[[c for c in subtype_cols if c != subtype]].any(axis=1)
        )
        subset = feature_table[pure_subtype | pure_baseline].copy()
        subset["_is_subtype"] = pure_subtype[pure_subtype | pure_baseline]

        result = known_groups_validity(subset, feature_cols, group_col="_is_subtype")
        result.insert(0, "pressure_type", subtype)
        rows.append(result)

    return pd.concat(rows, ignore_index=True)


def cronbach_alpha(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    align_signs: bool = True,
) -> float:
    """
    Cronbach's alpha on the (optionally sign-aligned) proxies, treated as
    "items" measuring one underlying construct. Rule-of-thumb bands:
    <0.5 unacceptable, 0.5-0.7 questionable/acceptable, >0.7 good -- but
    with only 3 items, alpha is mechanically harder to push high than
    with a long questionnaire, so treat this as a rough supporting
    statistic, not a pass/fail gate on its own.
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    clean = feature_table[feature_cols].dropna()
    X = _aligned(clean, feature_cols) if align_signs else clean[feature_cols]

    k = X.shape[1]
    item_variances = X.var(axis=0, ddof=1).sum()
    total_variance = X.sum(axis=1).var(ddof=1)
    if total_variance == 0:
        return float("nan")
    return (k / (k - 1)) * (1 - item_variances / total_variance)


def summarize_validity(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
) -> dict:
    """One-call bundle of all three angles, for a notebook to unpack and print."""
    feature_cols = feature_cols or DEFAULT_FEATURES
    return {
        "correlations": correlation_matrix(feature_table, feature_cols),
        "pca": run_pca(feature_table, feature_cols),
        "known_groups": known_groups_validity(feature_table, feature_cols),
        "cronbach_alpha": cronbach_alpha(feature_table, feature_cols),
    }

def apply_bh_correction(
    df: pd.DataFrame,
    pcol: str = "p",
    alpha: float = 0.05,
) -> pd.DataFrame:
    """
    Benjamini-Hochberg FDR correction across a family of p-values (e.g. the
    trajectory-slope p-values across all proxies, or the known-groups tests
    across proxies/pressure-subtypes). Testing multiple proxies/models
    against the same underlying laps inflates the false-positive rate if
    each p-value is read against alpha=0.05 in isolation; this adds
    `{pcol}_bh` (BH-adjusted p-value) and `significant_bh` (bool, adjusted
    p < alpha) columns and returns a copy. Rows with NaN in `pcol` are left
    untouched (not counted in the correction, not flagged significant).
    """
    from statsmodels.stats.multitest import multipletests

    out = df.copy()
    mask = out[pcol].notna()
    out[f"{pcol}_bh"] = np.nan
    out["significant_bh"] = False
    if mask.sum() == 0:
        return out
    reject, p_adj, _, _ = multipletests(out.loc[mask, pcol], alpha=alpha, method="fdr_bh")
    out.loc[mask, f"{pcol}_bh"] = p_adj
    out.loc[mask, "significant_bh"] = reject
    return out
