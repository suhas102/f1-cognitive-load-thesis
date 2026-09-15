"""
Supervised classification of high-pressure vs. baseline laps from the
telemetry-derived proxy variables (addresses RQ3).

Three models are fit and compared, deliberately rather than picking one
upfront:

  - Logistic Regression: interpretable coefficients (direction + magnitude
    of each proxy's association with the pressure state), the natural
    baseline model for a hypothesis-driven claim.
  - Random Forest: captures non-linear effects / interactions the linear
    model would miss, gives feature importances.
  - XGBoost: usually the strongest predictive performance of the three,
    paired with SHAP values for a more principled per-feature attribution
    than plain importances.

Laps from the same driver are NOT independent observations (repeated
measures), so evaluation uses GroupKFold grouped by Driver rather than a
random split -- this tests whether the pressure signature generalises to
drivers the model hasn't seen, not just to unseen laps from drivers it has.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, accuracy_score, f1_score
from sklearn.model_selection import GroupKFold, cross_validate
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

DEFAULT_FEATURES = [
    "throttle_smoothness",
    "braking_consistency",
    "sector_time_variance",
]


@dataclass
class ClassificationData:
    X: np.ndarray
    y: np.ndarray
    groups: np.ndarray
    feature_cols: list[str]
    clean: pd.DataFrame


def prepare_classification_data(
    feature_table: pd.DataFrame,
    feature_cols: list[str] | None = None,
    target: str = "high_pressure",
    group_col: str = "Driver",
) -> ClassificationData:
    """
    Drop rows with missing feature/target values, and return X, y, and a
    groups array (driver identity) for GroupKFold cross-validation.
    """
    feature_cols = feature_cols or DEFAULT_FEATURES
    cols_needed = feature_cols + [target, group_col]
    clean = feature_table.dropna(subset=cols_needed).copy()

    X = clean[feature_cols].to_numpy(dtype=float)
    y = clean[target].astype(int).to_numpy()
    groups = clean[group_col].to_numpy()

    return ClassificationData(X=X, y=y, groups=groups, feature_cols=feature_cols, clean=clean)


@dataclass
class ModelResult:
    name: str
    cv_metrics: pd.DataFrame  # per-fold accuracy / roc_auc / f1
    mean_metrics: dict
    fitted_model: object  # fit on the FULL dataset, for inspecting coefficients/importances
    scaler: StandardScaler | None = None


def _cv_scores(estimator, X: np.ndarray, y: np.ndarray, groups: np.ndarray, n_splits: int) -> pd.DataFrame:
    n_splits = min(n_splits, len(set(groups)))
    cv = GroupKFold(n_splits=n_splits)
    scoring = {"accuracy": "accuracy", "roc_auc": "roc_auc", "f1": "f1"}
    scores = cross_validate(estimator, X, y, groups=groups, cv=cv, scoring=scoring)
    return pd.DataFrame(
        {
            "fold": range(1, n_splits + 1),
            "accuracy": scores["test_accuracy"],
            "roc_auc": scores["test_roc_auc"],
            "f1": scores["test_f1"],
        }
    )


def fit_logistic_regression(data: ClassificationData, n_splits: int = 5, seed: int = 42) -> ModelResult:
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(data.X)

    estimator = LogisticRegression(max_iter=1000, random_state=seed)
    cv_metrics = _cv_scores(estimator, X_scaled, data.y, data.groups, n_splits)

    fitted = LogisticRegression(max_iter=1000, random_state=seed).fit(X_scaled, data.y)
    return ModelResult(
        name="logistic_regression",
        cv_metrics=cv_metrics,
        mean_metrics=cv_metrics[["accuracy", "roc_auc", "f1"]].mean().to_dict(),
        fitted_model=fitted,
        scaler=scaler,
    )


def fit_random_forest(data: ClassificationData, n_splits: int = 5, seed: int = 42, **rf_kwargs) -> ModelResult:
    defaults = dict(n_estimators=300, max_depth=5, min_samples_leaf=10, class_weight="balanced", random_state=seed)
    defaults.update(rf_kwargs)

    estimator = RandomForestClassifier(**defaults)
    cv_metrics = _cv_scores(estimator, data.X, data.y, data.groups, n_splits)

    fitted = RandomForestClassifier(**defaults).fit(data.X, data.y)
    return ModelResult(
        name="random_forest",
        cv_metrics=cv_metrics,
        mean_metrics=cv_metrics[["accuracy", "roc_auc", "f1"]].mean().to_dict(),
        fitted_model=fitted,
    )


def fit_xgboost(data: ClassificationData, n_splits: int = 5, seed: int = 42, **xgb_kwargs) -> ModelResult:
    n_pos = data.y.sum()
    n_neg = len(data.y) - n_pos
    scale_pos_weight = (n_neg / n_pos) if n_pos > 0 else 1.0

    defaults = dict(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=seed,
    )
    defaults.update(xgb_kwargs)

    estimator = XGBClassifier(**defaults)
    cv_metrics = _cv_scores(estimator, data.X, data.y, data.groups, n_splits)

    fitted = XGBClassifier(**defaults).fit(data.X, data.y)
    return ModelResult(
        name="xgboost",
        cv_metrics=cv_metrics,
        mean_metrics=cv_metrics[["accuracy", "roc_auc", "f1"]].mean().to_dict(),
        fitted_model=fitted,
    )


def compare_models(results: list[ModelResult]) -> pd.DataFrame:
    """One row per model: mean +/- std of each CV metric, for a summary table."""
    rows = []
    for r in results:
        row = {"model": r.name}
        for metric in ["accuracy", "roc_auc", "f1"]:
            row[f"{metric}_mean"] = r.cv_metrics[metric].mean()
            row[f"{metric}_std"] = r.cv_metrics[metric].std()
        rows.append(row)
    return pd.DataFrame(rows).set_index("model")


def logistic_regression_coefficients(result: ModelResult, feature_cols: list[str]) -> pd.DataFrame:
    """Standardized coefficients (since features were scaled before fitting) -- directly comparable magnitudes."""
    coefs = result.fitted_model.coef_[0]
    return pd.DataFrame({"feature": feature_cols, "coefficient": coefs}).sort_values(
        "coefficient", key=np.abs, ascending=False
    )


def feature_importances(result: ModelResult, feature_cols: list[str]) -> pd.DataFrame:
    """Works for random_forest and xgboost results (tree-based .feature_importances_)."""
    importances = result.fitted_model.feature_importances_
    return pd.DataFrame({"feature": feature_cols, "importance": importances}).sort_values(
        "importance", ascending=False
    )


def shap_values_for(result: ModelResult, data: ClassificationData):
    """
    Compute SHAP values for a tree-based model result (random_forest or
    xgboost). Returns the shap.Explanation object; caller handles plotting
    (kept out of this module so it stays notebook/matplotlib-free).
    """
    import shap

    explainer = shap.TreeExplainer(result.fitted_model)
    return explainer(data.X)
