"""
Objective 4: queryable race+driver -> confound-aware behavioural report.

Wraps a fitted Tier-2 classifier (see modeling.py) plus the merged,
confound-annotated feature table so a caller can ask "how did this driver's
control-input behaviour look in race X, and how does it compare to the
field, once tyre/compound confounds are accounted for?" for ANY driver/race
present in the table -- including combinations held out of a given
cross-validation fold, since generalization to unseen drivers is exactly
what the GroupKFold(Driver) CV in modeling.py already validates.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


def build_race_lookup(study_config) -> dict:
    """Map (location, year) -> race_label, built from the study's races.yaml.

    Two kinds of "location" both work, matched case-insensitively:
      - the country (`round`, e.g. "Brazil") -- but only for a year in
        which that country hosted exactly one Grand Prix. When a country
        hosted more than one race that season (USA: Miami/Austin/Las
        Vegas; Italy: Imola/Monza in some years), the country name alone
        is ambiguous and is deliberately left out of the lookup.
      - the venue city (`location`, e.g. "Miami", "Suzuka") -- always
        unique, so this always works, including for multi-race countries.

    This is the glue that lets a human type a location + year instead of
    the internal race_label the rest of the pipeline uses.
    """
    from collections import defaultdict

    by_country_year = defaultdict(list)
    for race_spec in study_config.races:
        by_country_year[(str(race_spec.round).strip().lower(), int(race_spec.year))].append(race_spec)

    lookup = {}
    for race_spec in study_config.races:
        year = int(race_spec.year)
        location = getattr(race_spec, "location", None)
        if location:
            lookup[(str(location).strip().lower(), year)] = race_spec.label
        country_key = (str(race_spec.round).strip().lower(), year)
        if len(by_country_year[country_key]) == 1:
            lookup[country_key] = race_spec.label
    return lookup


@dataclass
class BehaviouralReport:
    driver: str
    race_label: str
    n_laps: int
    mean_predicted_load: float
    pct_laps_high_load: float
    field_mean_load: float
    load_vs_field: float
    high_pressure_laps: list
    tyre_compounds_used: list
    mean_tyre_age: float
    model_name: str
    model_cv_roc_auc: float
    text: str


class BehaviouralLoadReportTool:
    """
    Parameters
    ----------
    model_result : modeling.ModelResult
        A fitted Tier-2 classifier (e.g. from modeling.fit_random_forest),
        trained with modeling.prepare_classification_data on the study's
        pooled feature table.
    feature_table : pd.DataFrame
        The full, confound-annotated lap-level feature table (concatenated
        across races) the model was trained/evaluated on -- must contain
        `feature_cols`, "Driver", "LapNumber", "Compound", "TyreLife", and
        a race-label column identifying which race each row came from.
    feature_cols : list[str]
        Same feature columns used to train `model_result`.
    race_label_col : str
        Column in `feature_table` identifying the race (default "race_label").
    """

    def __init__(
        self,
        model_result,
        feature_table: pd.DataFrame,
        feature_cols: list[str],
        race_label_col: str = "race_label",
    ):
        self.model_result = model_result
        self.feature_table = feature_table
        self.feature_cols = feature_cols
        self.race_label_col = race_label_col

    def _clean_table(self) -> pd.DataFrame:
        """Rows usable for reporting: no missing values in any column the
        model or the report needs. Shared by `available_queries` and
        `report` so a driver/race never appears as "available" and then
        fails with "no data" once the same missing-value filter is applied.
        """
        needed = self.feature_cols + ["Driver", "LapNumber", self.race_label_col]
        return self.feature_table.dropna(subset=needed).copy()

    def _predicted_load(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feature_cols].to_numpy(dtype=float)
        model = self.model_result.fitted_model
        if self.model_result.scaler is not None:
            X = self.model_result.scaler.transform(X)
        return model.predict_proba(X)[:, 1]

    def _resolve_driver(self, driver: str, race_label: str) -> str:
        """Resolve a user-typed driver identifier -- a 3-letter code in any
        case, or a substring of a full/broadcast name if such a column is
        present in the feature table -- to the exact Driver code used
        internally. Raises ValueError listing the valid codes for this race
        if nothing matches, rather than silently returning the wrong driver.
        """
        clean = self._clean_table()
        race_df = clean[clean[self.race_label_col] == race_label]
        codes = sorted(race_df["Driver"].dropna().astype(str).unique().tolist())

        driver_str = str(driver).strip()
        upper = driver_str.upper()
        if upper in codes:
            return upper

        for name_col in ("FullName", "DriverFullName", "BroadcastName", "DriverName"):
            if name_col in race_df.columns:
                matches = race_df[
                    race_df[name_col].astype(str).str.lower().str.contains(
                        driver_str.lower(), na=False
                    )
                ]
                found = sorted(matches["Driver"].dropna().astype(str).unique().tolist())
                if len(found) == 1:
                    return found[0]
                if len(found) > 1:
                    raise ValueError(
                        f"driver={driver!r} matched multiple drivers in "
                        f"race_label={race_label!r}: {found}. Use the 3-letter code instead."
                    )

        raise ValueError(
            f"Could not resolve driver={driver!r} for race_label={race_label!r}. "
            f"Available driver codes: {codes}"
        )

    def report_from_query(
        self, driver: str, location: str, year: int, race_lookup: dict
    ) -> "BehaviouralReport":
        """Same as `report`, but takes the human-facing (driver, location,
        year) triple instead of the internal (race_label, driver-code)
        pair -- `race_lookup` comes from `build_race_lookup(study_config)`.
        """
        key = (str(location).strip().lower(), int(year))
        if key not in race_lookup:
            raise ValueError(
                f"No race found for location={location!r}, year={year!r}. "
                f"Known (location, year) pairs: {sorted(race_lookup.keys())}"
            )
        race_label = race_lookup[key]
        resolved_driver = self._resolve_driver(driver, race_label)
        return self.report(race_label=race_label, driver=resolved_driver)

    def batch_report_from_csv(
        self,
        csv_path: str,
        race_lookup: dict,
        output_csv_path: str | None = None,
    ) -> pd.DataFrame:
        """H4: read a CSV with columns `driver`, `location`, `year` -- one
        query per row -- and return a DataFrame with the full behavioural-
        load report for each row (mean predicted load, % high-load laps,
        tyre info, model used, and the full human-readable report text).

        A row that can't be resolved (unknown race, unknown driver, or a
        driver with no usable data for that race) gets an `error` message
        in its own row instead of failing the whole batch. If
        `output_csv_path` is given, the result is also written there.
        """
        queries = pd.read_csv(csv_path)
        queries.columns = [c.strip().lower() for c in queries.columns]
        required_cols = {"driver", "location", "year"}
        missing_cols = required_cols - set(queries.columns)
        if missing_cols:
            raise ValueError(f"Input CSV is missing required columns: {sorted(missing_cols)}")

        rows = []
        for _, q in queries.iterrows():
            row = {"driver": q["driver"], "location": q["location"], "year": q["year"]}
            try:
                rep = self.report_from_query(q["driver"], q["location"], q["year"], race_lookup)
                row.update(
                    {
                        "race_label": rep.race_label,
                        "resolved_driver": rep.driver,
                        "n_laps": rep.n_laps,
                        "mean_predicted_load": rep.mean_predicted_load,
                        "pct_laps_high_load": rep.pct_laps_high_load,
                        "field_mean_load": rep.field_mean_load,
                        "load_vs_field": rep.load_vs_field,
                        "high_pressure_laps": rep.high_pressure_laps,
                        "tyre_compounds_used": rep.tyre_compounds_used,
                        "mean_tyre_age": rep.mean_tyre_age,
                        "model_name": rep.model_name,
                        "model_cv_roc_auc": rep.model_cv_roc_auc,
                        "report_text": rep.text,
                        "error": "",
                    }
                )
            except ValueError as e:
                row.update(
                    {
                        "race_label": "",
                        "resolved_driver": "",
                        "n_laps": None,
                        "mean_predicted_load": None,
                        "pct_laps_high_load": None,
                        "field_mean_load": None,
                        "load_vs_field": None,
                        "high_pressure_laps": None,
                        "tyre_compounds_used": None,
                        "mean_tyre_age": None,
                        "model_name": "",
                        "model_cv_roc_auc": None,
                        "report_text": "",
                        "error": str(e),
                    }
                )
            rows.append(row)

        result = pd.DataFrame(rows)
        if output_csv_path is not None:
            result.to_csv(output_csv_path, index=False)
        return result

    def available_queries(self) -> pd.DataFrame:
        """Every (race, driver) combination this tool can currently report on."""
        return (
            self._clean_table()[[self.race_label_col, "Driver"]]
            .drop_duplicates()
            .sort_values([self.race_label_col, "Driver"])
            .reset_index(drop=True)
        )

    def report(self, race_label: str, driver: str) -> BehaviouralReport:
        clean = self._clean_table()

        race_df = clean[clean[self.race_label_col] == race_label]
        if race_df.empty:
            raise ValueError(f"No data for race_label={race_label!r}")

        driver_df = race_df[race_df["Driver"] == driver]
        if driver_df.empty:
            raise ValueError(f"No data for driver={driver!r} in race_label={race_label!r}")

        driver_df = driver_df.copy()
        driver_df["predicted_load"] = self._predicted_load(driver_df)
        race_df = race_df.copy()
        race_df["predicted_load"] = self._predicted_load(race_df)

        mean_load = float(driver_df["predicted_load"].mean())
        field_mean = float(race_df["predicted_load"].mean())
        pct_high = float((driver_df["predicted_load"] >= 0.5).mean() * 100)
        high_laps = (
            driver_df.loc[driver_df["predicted_load"] >= 0.5, "LapNumber"]
            .sort_values()
            .tolist()
        )

        compounds = (
            sorted(driver_df["Compound"].dropna().astype(str).unique().tolist())
            if "Compound" in driver_df
            else []
        )
        mean_tyre_age = (
            float(driver_df["TyreLife"].mean()) if "TyreLife" in driver_df else float("nan")
        )

        cv = self.model_result.cv_metrics
        cv_auc = float(cv["roc_auc"].mean()) if cv is not None and "roc_auc" in cv else float("nan")

        text = (
            f"{driver} — {race_label}\n"
            f"  Laps analysed: {len(driver_df)}\n"
            f"  Mean predicted cognitive-load probability: {mean_load:.3f} "
            f"(field mean this race: {field_mean:.3f}, "
            f"{'above' if mean_load > field_mean else 'below'} field by "
            f"{abs(mean_load - field_mean):.3f})\n"
            f"  Laps flagged high-load (p>=0.5): {pct_high:.1f}% "
            f"({len(high_laps)} laps: {high_laps})\n"
            f"  Tyre compounds used: {compounds}, mean tyre age at sample: {mean_tyre_age:.1f} laps\n"
            f"  Model: {self.model_result.name} "
            f"(GroupKFold driver-held-out ROC-AUC: {cv_auc:.3f})\n"
            f"  Note: predicted load already accounts for tyre compound/age via the confound-\n"
            f"  controlled feature pipeline; the model was validated on driver-grouped folds so\n"
            f"  this driver/race need not have been in the training fold to be reported on."
        )

        return BehaviouralReport(
            driver=driver,
            race_label=race_label,
            n_laps=len(driver_df),
            mean_predicted_load=mean_load,
            pct_laps_high_load=pct_high,
            field_mean_load=field_mean,
            load_vs_field=mean_load - field_mean,
            high_pressure_laps=high_laps,
            tyre_compounds_used=compounds,
            mean_tyre_age=mean_tyre_age,
            model_name=self.model_result.name,
            model_cv_roc_auc=cv_auc,
            text=text,
        )
