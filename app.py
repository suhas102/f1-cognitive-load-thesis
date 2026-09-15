from __future__ import annotations

import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext, ttk

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "src"))

# Reuse every helper already written (and already proven working) for run_h4.py
from run_h4 import (  # noqa: E402
    TIER2_FEATURES,
    build_pooled_feature_table,
    build_study_config,
    fetch_all_races,
    fit_best_model,
)
from f1_cognitive_load import report  # noqa: E402

YEARS = [2023, 2024, 2025]
CACHE_DIR = REPO_ROOT / "data" / "raw"
CONFIG_PATH = REPO_ROOT / "config" / "races.yaml"


class H4App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("H4 -- Driver Cognitive-Load Report")
        self.geometry("720x560")
        self.minsize(600, 420)

        self.report_tool = None
        self.race_lookup = None

        self._build_widgets()
        self._set_status("Loading model and cached race data, please wait...")
        self._set_inputs_enabled(False)

        # Do the (slow, one-time) setup off the UI thread so the window
        # stays responsive and shows the "loading" message immediately.
        threading.Thread(target=self._load_model, daemon=True).start()

    def _build_widgets(self):
        pad = {"padx": 8, "pady": 6}

        form = ttk.Frame(self)
        form.pack(fill="x", **pad)

        ttk.Label(form, text="Driver (3-letter code, e.g. HAM):").grid(row=0, column=0, sticky="w")
        self.driver_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.driver_var, width=20).grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(form, text="Location (e.g. Miami, Monaco, Brazil):").grid(row=1, column=0, sticky="w")
        self.location_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.location_var, width=20).grid(row=1, column=1, sticky="w", padx=6)

        ttk.Label(form, text="Year (2023-2025):").grid(row=2, column=0, sticky="w")
        self.year_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.year_var, width=20).grid(row=2, column=1, sticky="w", padx=6)

        self.submit_btn = ttk.Button(form, text="Get report", command=self._on_submit)
        self.submit_btn.grid(row=3, column=0, columnspan=2, pady=10)

        self.list_btn = ttk.Button(form, text="Show known locations/years", command=self._on_show_known)
        self.list_btn.grid(row=3, column=2, padx=10)

        self.status_label = ttk.Label(self, text="", foreground="#555")
        self.status_label.pack(fill="x", padx=10)

        self.output = scrolledtext.ScrolledText(self, wrap="word", font=("Consolas", 10))
        self.output.pack(fill="both", expand=True, padx=10, pady=10)
        self.output.configure(state="disabled")

    def _set_status(self, text: str):
        self.status_label.config(text=text)

    def _set_inputs_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.submit_btn.config(state=state)
        self.list_btn.config(state=state)

    def _write_output(self, text: str):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.configure(state="disabled")

    def _load_model(self):
        try:
            study_config = build_study_config(YEARS, CONFIG_PATH)
            race_data = fetch_all_races(study_config, CACHE_DIR)
            if not race_data:
                self._set_status("No cached race data found -- run run_h4.py once first to fetch it.")
                return

            pooled = build_pooled_feature_table(race_data)
            best_result = fit_best_model(pooled)

            self.report_tool = report.BehaviouralLoadReportTool(
                best_result,
                feature_table=pooled,
                feature_cols=TIER2_FEATURES,
                race_label_col="race_label",
            )
            self.race_lookup = report.build_race_lookup(study_config)

            self.after(0, self._on_model_ready)
        except Exception as e:  # noqa: BLE001 -- surface any setup error to the UI, not just the console
            msg = f"Failed to load model/data:\n{e}"
            self.after(0, lambda: self._set_status("Setup failed -- see output box."))
            self.after(0, lambda: self._write_output(msg))

    def _on_model_ready(self):
        self._set_status("Ready. Type a driver, location and year, then click \"Get report\".")
        self._set_inputs_enabled(True)

    def _on_show_known(self):
        if not self.race_lookup:
            return
        lines = ["Known (location, year) combinations:"]
        for (location, year), race_label in sorted(self.race_lookup.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            lines.append(f"  {location.title()}, {year}  ->  {race_label}")
        self._write_output("\n".join(lines))

    def _on_submit(self):
        driver = self.driver_var.get().strip()
        location = self.location_var.get().strip()
        year = self.year_var.get().strip()

        if not driver or not location or not year:
            self._write_output("Please fill in driver, location and year.")
            return
        try:
            year_int = int(year)
        except ValueError:
            self._write_output(f"Year must be a number (2023-2025), got {year!r}.")
            return

        try:
            rep = self.report_tool.report_from_query(driver, location, year_int, self.race_lookup)
            self._write_output(rep.text)
        except ValueError as e:
            self._write_output(f"Could not generate report:\n{e}")


if __name__ == "__main__":
    app = H4App()
    app.mainloop()
