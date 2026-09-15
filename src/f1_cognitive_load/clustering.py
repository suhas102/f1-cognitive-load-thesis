"""
Cluster laps (or driver-level aggregates) into cognitive performance
profiles using the proxy variables from features.py.

Two levels of clustering are supported:

  - lap-level: cluster individual laps to see whether high-pressure laps
    separate from baseline laps in feature space (addresses RQ3).
  - driver-level: aggregate features per driver and cluster drivers to see
    whether distinct cognitive-performance profiles emerge (addresses RQ4).

KMeans is used as the default (interpretable, well-understood), with
silhouette score used to help select k. A second, independent clustering
method -- Random Forest proximity + hierarchical clustering -- is also
provided for RQ4, so the driver-profile claim rests on agreement between
two different methods rather than one algorithm's idiosyncrasies.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform
from scipy.stats import kruskal
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.preprocessing import StandardScaler

DEFAULT_FEATURES = [
    "throttle_smoothness",
    "braking_consistency",
    "sector_time_variance",
]


@dataclass
class ClusterResult:
    labels: np.ndarray
    model: KMeans
    scaler: StandardScaler
    silhouette: float
    feature_cols: list[str]


def _prepare(df: pd.DataFrame, feature_cols: list[str]) -> tuple[pd.DataFrame, StandardScaler, np.ndarray]:
    clean = df.dropna(subset=feature_cols).copy()
    scaler = StandardScaler()
    X = scaler.fit_transform(clean[feature_cols])
    return clean, scaler, X


def select_k(X: np.ndarray, k_range: range = range(2, 7), seed: int = 42) -> pd.DataFrame:
    """Fit KMeans across a range of k and report silhouette score for each, to help pick k."""
    rows = []
    for k in k_range:
        if k >= len(X):
            continue
        model = KMeans(n_clusters=k, n_init=10, random_state=seed)
        labels = model.fit_predict(X)
        score = silhouette_score(X, labels) if len(set(labels)) > 1 else float("nan")
        rows.append({"k": k, "silhouette": score, "inertia": model.inertia_})
    return pd.DataFrame(rows)


def cluster_laps(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    k: int = 3,
    seed: int = 42,
) -> tuple[pd.DataFrame, ClusterResult]:
    """
    Cluster individual laps in `feature_table` (output of
    features.build_feature_table) into k cognitive-performance profiles.
    Rows with missing feature values are dropped before clustering (usually
    the first few laps of a rolling window, or laps with no valid telemetry).
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    clean, scaler, X = _prepare(feature_table, feature_cols)

    model = KMeans(n_clusters=k, n_init=10, random_state=seed)
    labels = model.fit_predict(X)
    silhouette = silhouette_score(X, labels) if len(set(labels)) > 1 else float("nan")

    clean = clean.copy()
    clean["cluster"] = labels

    result = ClusterResult(labels=labels, model=model, scaler=scaler, silhouette=silhouette, feature_cols=feature_cols)
    return clean, result


def cluster_drivers(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    k: int = 3,
    seed: int = 42,
    agg: str = "mean",
) -> tuple[pd.DataFrame, ClusterResult]:
    """
    Aggregate features per driver (default: mean across all laps) and
    cluster drivers into cognitive-performance profiles (addresses RQ4).
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    driver_level = feature_table.groupby("Driver")[feature_cols].agg(agg).reset_index()
    clean, scaler, X = _prepare(driver_level, feature_cols)

    model = KMeans(n_clusters=k, n_init=10, random_state=seed)
    labels = model.fit_predict(X)
    silhouette = silhouette_score(X, labels) if len(set(labels)) > 1 else float("nan")

    clean = clean.copy()
    clean["cluster"] = labels

    result = ClusterResult(labels=labels, model=model, scaler=scaler, silhouette=silhouette, feature_cols=feature_cols)
    return clean, result


@dataclass
class RFClusterResult:
    labels: np.ndarray
    proximity: np.ndarray
    linkage_matrix: np.ndarray
    feature_cols: list[str]
    ids: list  # e.g. driver names, in the same order as labels/proximity rows


def _rf_proximity_matrix(X: np.ndarray, n_estimators: int = 500, seed: int = 42) -> np.ndarray:
    """
    Unsupervised Random Forest proximity matrix (Breiman & Cutler's trick):
    fit an RF to distinguish the real data from a synthetic "unstructured"
    version of it (each feature independently permuted, which destroys any
    real correlation structure but keeps each feature's marginal distribution).
    Samples that end up in the same leaf across many trees are behaviourally
    similar; the resulting proximity matrix is a similarity measure that
    doesn't assume clusters are spherical (unlike raw Euclidean distance +
    KMeans), so it's a genuinely independent check on the KMeans result.
    """
    rng = np.random.default_rng(seed)
    n, p = X.shape

    synthetic = np.column_stack([rng.permutation(X[:, j]) for j in range(p)])
    X_combined = np.vstack([X, synthetic])
    y_combined = np.concatenate([np.ones(n), np.zeros(n)])

    rf = RandomForestClassifier(n_estimators=n_estimators, min_samples_leaf=1, random_state=seed)
    rf.fit(X_combined, y_combined)

    leaves = rf.apply(X[:n])  # (n_samples, n_trees) leaf index per tree, real samples only
    n_trees = leaves.shape[1]

    proximity = np.zeros((n, n))
    for t in range(n_trees):
        same_leaf = leaves[:, t][:, None] == leaves[:, t][None, :]
        proximity += same_leaf
    proximity /= n_trees
    return proximity


def rf_cluster_drivers(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    k: int = 3,
    seed: int = 42,
    agg: str = "mean",
    n_estimators: int = 500,
) -> tuple[pd.DataFrame, RFClusterResult]:
    """
    RF-proximity + hierarchical clustering of driver-level aggregates
    (addresses RQ4's "machine learning clustering" requirement via a method
    independent of KMeans). Distance = 1 - proximity; average linkage.
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    driver_level = feature_table.groupby("Driver")[feature_cols].agg(agg).reset_index()
    clean, scaler, X = _prepare(driver_level, feature_cols)

    proximity = _rf_proximity_matrix(X, n_estimators=n_estimators, seed=seed)
    distance = 1 - proximity
    np.fill_diagonal(distance, 0)
    distance = (distance + distance.T) / 2  # guard against float asymmetry before squareform

    condensed = squareform(distance, checks=False)
    Z = linkage(condensed, method="average")
    labels = fcluster(Z, t=k, criterion="maxclust") - 1  # zero-index to match KMeans convention

    clean = clean.copy()
    clean["cluster"] = labels

    result = RFClusterResult(
        labels=labels, proximity=proximity, linkage_matrix=Z, feature_cols=feature_cols, ids=list(clean["Driver"])
    )
    return clean, result


def compare_clusterings(labels_a: np.ndarray, labels_b: np.ndarray) -> float:
    """
    Adjusted Rand Index between two cluster labelings of the SAME items in
    the SAME order (e.g. KMeans vs. RF-proximity driver clusters). 1.0 =
    identical grouping, ~0.0 = no better than random agreement. Used to
    check whether the two independent clustering methods for RQ4 agree.
    """
    return adjusted_rand_score(labels_a, labels_b)


def kruskal_wallis_by_driver(feature_table: pd.DataFrame, feature_cols: list[str] | None = None) -> pd.DataFrame:
    """
    Non-parametric test of whether each proxy feature differs across
    drivers (RQ4's "differ meaningfully between drivers" claim), before/
    alongside the clustering itself. One row per feature: H-statistic, p.
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    rows = []
    for col in feature_cols:
        groups = [g[col].dropna().to_numpy() for _, g in feature_table.groupby("Driver") if g[col].notna().any()]
        groups = [g for g in groups if len(g) > 0]
        if len(groups) < 2:
            rows.append({"feature": col, "H": float("nan"), "p": float("nan"), "n_drivers": len(groups)})
            continue
        stat, p = kruskal(*groups)
        rows.append({"feature": col, "H": stat, "p": p, "n_drivers": len(groups)})
    return pd.DataFrame(rows)


def compare_high_pressure_vs_baseline(feature_table: pd.DataFrame, feature_cols: list[str] | None = None) -> pd.DataFrame:
    """
    Simple descriptive comparison (mean +/- std) of each proxy feature
    between high-pressure and baseline laps, as a first pass at RQ3 before
    formal hypothesis testing (e.g. Mann-Whitney U in the notebook).
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    if "high_pressure" not in feature_table.columns:
        raise ValueError("feature_table must include a 'high_pressure' column (see features.flag_high_pressure_windows)")

    return (
        feature_table.groupby("high_pressure")[feature_cols]
        .agg(["mean", "std", "count"])
    )
