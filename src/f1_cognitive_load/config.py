"""Load and validate the races.yaml configuration file."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "races.yaml"
DEFAULT_LOCAL_DATASET_PATHS = REPO_ROOT / "config" / "local_dataset_paths.yaml"


@dataclass
class RaceSpec:
    year: int
    round: int
    session: str
    label: str
    # OpenF1 venue "location" (city, e.g. "Miami", "Suzuka") -- optional, but
    # required to disambiguate when `round` (country) hosts more than one
    # Grand Prix in the same year (USA: Miami/Austin/Las Vegas; Italy:
    # Imola/Monza in some years). When absent, `round` alone must uniquely
    # identify one race that year.
    location: str | None = None


@dataclass
class StudyConfig:
    races: list[RaceSpec]
    driver_filter: list[str]


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> StudyConfig:
    path = Path(path)
    with open(path, "r") as f:
        raw = yaml.safe_load(f)

    races = [
        RaceSpec(
            year=r["year"],
            round=r["round"],
            session=r.get("session", "R"),
            label=r["label"],
            location=r.get("location"),
        )
        for r in raw.get("races", [])
    ]
    driver_filter = (raw.get("drivers") or {}).get("include") or []

    if not races:
        raise ValueError(f"No races defined in {path}")

    return StudyConfig(races=races, driver_filter=driver_filter)
