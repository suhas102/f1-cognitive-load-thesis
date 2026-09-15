# Inferring Cognitive Load and Decision-Making Under Pressure in Formula 1 Drivers

A telemetry-based behavioural modelling pipeline built for an MSc thesis (Artificial
Intelligence and Data Science, Keele University, module CSC-44120, supervised by
Dr Nadia Kanwal). It tests — rather than assumes — whether telemetry-derived
behavioural proxies (throttle smoothness, braking consistency, sector-time variance)
actually track cognitive load in Formula 1 drivers, using the public [OpenF1
API](https://openf1.org) across the full 2023–2025 calendar (61 races, 28 drivers,
65,763 laps).

The project is organised around four hypotheses:

| | Hypothesis | Outcome |
|---|---|---|
| H1 | The three proxies form one valid construct | Not supported as a single construct (Cronbach's α = 0.096); each proxy is individually significant, but they behave differently from one another |
| H2 | Each proxy shifts systematically over a stint | Supported — all three proxies decline significantly across a stint, even after controlling for tyre age/compound |
| H3 | Behavioural signatures classify high-pressure laps, including for unseen drivers | Supported — XGBoost distinguishes high-pressure laps with ROC-AUC ≈ 0.740 under driver-grouped cross-validation |
| H4 | The best H3 model can power a queryable reporting tool | Supported — a working desktop tool (`app.py` / `run_h4.py`) generates confound-aware, per-driver, per-race load reports |

## Repository layout

```
.
├── app.py                       # Tkinter desktop app (H4): query a driver/race, get a load report
├── run_h4.py                    # CLI/batch driver for H4 — fetches OpenF1 data, fits the H3 model, runs reports
├── requirements.txt
├── driver_queries_example.csv   # Example batch input for run_h4.py --input
├── config/
│   └── races.yaml               # Cached OpenF1 race calendar (year, round, location, label)
├── src/f1_cognitive_load/
│   ├── openf1_fetch.py          # OpenF1 API client — fetching, caching (parquet), rate-limit backoff
│   ├── features.py              # Feature engineering: the three behavioural proxies
│   ├── modeling.py              # H3 classifiers (logistic regression, random forest, XGBoost) + evaluation
│   ├── validity.py              # H1 construct-validity tests (PCA, Cronbach's alpha, known-groups effect sizes)
│   ├── trajectory.py            # H2 within-stint trajectory (mixed-effects models)
│   ├── clustering.py            # Exploratory driver/behavioural clustering
│   ├── report.py                # H4 report generation and batch CSV interface
│   └── config.py                # Study configuration loading (StudyConfig, RaceSpec)
└── presentation/
    └── build_deck.js            # pptxgenjs script that generates the thesis defence slide deck
```

## Requirements

- Python 3.11+ (tested on 3.13)
- Internet access to `https://api.openf1.org` (free tier: 3 req/s, 30 req/min — no API key needed for historical seasons)

```bash
pip install -r requirements.txt
```

## Running the H4 tool

### Desktop app

```bash
python app.py
```

Enter a driver code (e.g. `HAM`), a location (e.g. `Monaco`), and a year (2023–2025),
then click **Get report**. The first run fetches and caches the full calendar and
race data locally (parquet files under `data/raw/`, ~45–75 minutes); subsequent runs
reuse that cache and are near-instant.

### Batch CLI

```bash
python run_h4.py --input driver_queries_example.csv --output driver_reports.csv \
    --years 2023 2024 2025 --cache-dir ./data/raw
```

`driver_queries_example.csv` needs exactly three columns: `driver,location,year`.

Every report already accounts for tyre compound and tyre age via the same
confound-controlled pipeline used throughout the thesis, and the underlying model
was validated with driver-grouped (leakage-safe) cross-validation — so a driver/race
being queryable does not mean it was in the model's test fold in a way that would
inflate its own reported numbers.

## Rebuilding the presentation

```bash
cd presentation
npm install pptxgenjs
node build_deck.js
```

This regenerates `ThesisPresentation.pptx` in the repository root. The script expects
a `presentation/figures/` folder containing the referenced pipeline diagram, SHAP
summary plot, and H4 app screenshot (not included in this repository — add your own
or regenerate them from the thesis figures).

## Data

Fetched OpenF1 race data (`data/`) is not committed to this repository — it's
regenerated automatically the first time `app.py` or `run_h4.py` is run, and is
excluded via `.gitignore` since it's large (~5MB per race) and fully reproducible
from the public API.

## Notes on data provenance

Race discovery (`config/races.yaml`) is cached rather than re-fetched from OpenF1's
`/meetings` endpoint on every run, since race-weekend metadata for a completed season
never changes. 10 of 71 attempted 2023–2025 race weekends were dropped automatically
by the pipeline (logged, not patched or imputed) due to null merge keys, mismatched
timestamp formats, or a missing endpoint — leaving the 61-race, 65,763-lap analytic
sample used throughout.

## Author

Suhas Suresh — MSc Artificial Intelligence and Data Science, Keele University
