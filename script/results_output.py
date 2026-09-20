"""Compute analysis once, then export full-precision results and LaTeX macros.

The fixed years, population filters, institutional policy formula, unweighted
cross-state statistics, and sample standard deviation reproduce the assignment.
This module has no plotting dependency. It does not change the cleaned sample.
"""

import hashlib
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pandas as pd

from analysis_validation import checked_divide

START_YEAR = 2010
END_YEAR = 2015
AID_YEAR = 2015
POLICY_LINEAR = 1750.0
POLICY_QUADRATIC = 0.15


def _check_panel(df):
    """Reject incomplete/invalid inputs instead of silently changing the sample."""
    required = [
        "ID_IPEDS", "stabbr", "year", "public", "degree_bach",
        "enroll_ftug", "grant_federal",
    ]
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    panel = df[required].copy()
    if panel.empty or panel.isna().any().any():
        raise ValueError("Analysis requires a nonempty, complete-case cleaned panel.")
    for column in ("ID_IPEDS", "stabbr"):
        if panel[column].astype("string").str.strip().eq("").any():
            raise ValueError(f"Blank {column} in cleaned panel.")
    for column in ("year", "public", "degree_bach", "enroll_ftug", "grant_federal"):
        panel[column] = pd.to_numeric(panel[column], errors="raise")
        values = panel[column].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(f"{column} must be finite and nonnegative.")
    for column in ("public", "degree_bach"):
        if not panel[column].isin([0, 1]).all():
            raise ValueError(f"{column} must contain only 0 and 1.")
    if panel["enroll_ftug"].mod(1).ne(0).any():
        raise ValueError("enroll_ftug must contain whole-number counts.")
    expected = set(range(START_YEAR, END_YEAR + 1))
    if set(panel["year"].unique()) != expected:
        raise ValueError(f"This assignment and memo require exactly {START_YEAR}-{END_YEAR}.")
    if panel.duplicated(["ID_IPEDS", "year"]).any():
        raise ValueError("Duplicate institution-year observations.")
    if not panel.groupby("ID_IPEDS")["year"].nunique().eq(len(expected)).all():
        raise ValueError("Input is not a balanced institution-year panel.")
    return panel


def describe_state_aid(values, *, label):
    """Unweighted statistics across state rates; sample SD and linear quantiles."""
    if len(values) < 2 or not np.isfinite(values.to_numpy(dtype=float)).all():
        raise ValueError(f"{label}: need at least two finite state rates.")
    q = values.quantile([0.10, 0.25, 0.75, 0.90], interpolation="linear")
    stats = {
        "mean": float(values.mean()),
        "median": float(values.median()),
        "std": float(values.std(ddof=1)),
        "min": float(values.min()),
        "max": float(values.max()),
        "p10": float(q.loc[0.10]),
        "p25": float(q.loc[0.25]),
        "p75": float(q.loc[0.75]),
        "p90": float(q.loc[0.90]),
    }
    stats["range"] = stats["max"] - stats["min"]
    stats["ratio_90_10"] = float(checked_divide(
        stats["p90"], stats["p10"], label=f"{label}: 90/10 ratio"
    ))
    return stats


def calculate_results(df):
    """Return one results object consumed by the figures, JSON, CSV, and LaTeX.

    Returns a dictionary with summary (plain Python values), enrollment_by_year
    (DataFrame), and state_results (DataFrame). No files are written here.
    """
    panel = _check_panel(df)
    public_two_year = panel.loc[panel["public"].eq(1) & panel["degree_bach"].eq(0)]
    yearly = public_two_year.groupby("year")["enroll_ftug"].sum(min_count=1)
    if set(yearly.index) != set(range(START_YEAR, END_YEAR + 1)):
        raise ValueError("Public two-year enrollment is unavailable in a required year.")
    start = float(yearly.loc[START_YEAR])
    end = float(yearly.loc[END_YEAR])
    change_pct = 100 * float(checked_divide(
        end - start, start, label="Public two-year enrollment change"
    ))

    aid = panel.loc[panel["year"].eq(AID_YEAR)].copy()
    # Cast before squaring to avoid integer overflow; apply at the institution level.
    enrollment = aid["enroll_ftug"].astype(float)
    aid["grant_simulated"] = POLICY_LINEAR * enrollment + POLICY_QUADRATIC * enrollment**2
    state = aid.groupby("stabbr")[[
        "grant_federal", "grant_simulated", "enroll_ftug"
    ]].sum(min_count=1)
    state["per_student_aid"] = checked_divide(
        state["grant_federal"], state["enroll_ftug"], label="Current state aid"
    )
    state["simulated_aid_per_student"] = checked_divide(
        state["grant_simulated"], state["enroll_ftug"], label="Simulated state aid"
    )
    if not {"NY", "VT"}.issubset(state.index):
        raise ValueError("Both NY and VT are required by the comparison and memo.")
    state["budget_impact"] = state["grant_simulated"] - state["grant_federal"]
    state["outcome"] = np.select(
        [state["budget_impact"].gt(0), state["budget_impact"].lt(0)],
        ["Net increase", "Net decrease"], default="No change",
    )
    current = describe_state_aid(state["per_student_aid"], label="Current aid")
    simulated = describe_state_aid(state["simulated_aid_per_student"], label="Simulated aid")
    summary = {
        "definitions": {
            "start_year": START_YEAR, "end_year": END_YEAR, "aid_year": AID_YEAR,
            "year_convention": "Academic year starting year",
            "enrollment_sample": "public == 1 and degree_bach == 0",
            "aid_sample": "All retained institutions in the aid year",
            "state_rate": "Sum of grants divided by sum of enrollment within state",
            "dispersion_weighting": "Unweighted across included state rates",
            "standard_deviation_ddof": 1,
            "quantile_interpolation": "linear",
            "policy_formula": "1750 * enroll_ftug + 0.15 * enroll_ftug**2, per institution",
            "policy_linear": POLICY_LINEAR, "policy_quadratic": POLICY_QUADRATIC,
            "money_unit": "Dollars as recorded; no inflation adjustment",
            "change_percent_unit": "Percent, not fraction or percentage points",
            "budget_scope": "Retained sample only, simulated minus observed",
        },
        "sample": {
            "institutions": int(panel["ID_IPEDS"].nunique()),
            "institution_years": len(panel), "states_in_aid_year": len(state),
        },
        "enrollment": {"start": start, "end": end, "change_percent": change_pct},
        "ny_vt": {
            "NY": float(state.loc["NY", "per_student_aid"]),
            "VT": float(state.loc["VT", "per_student_aid"]),
            "NY_minus_VT": float(state.loc["NY", "per_student_aid"] - state.loc["VT", "per_student_aid"]),
        },
        "current": current,
        "simulated": simulated,
        "budget": {
            "current_total": float(state["grant_federal"].sum(min_count=1)),
            "simulated_total": float(state["grant_simulated"].sum(min_count=1)),
            "change": float(state["budget_impact"].sum(min_count=1)),
            "states_net_increase": int(state["budget_impact"].gt(0).sum()),
            "states_net_decrease": int(state["budget_impact"].lt(0).sum()),
            "states_unchanged": int(state["budget_impact"].eq(0).sum()),
        },
    }
    # Reject any non-finite scalar before it can appear in saved results or prose.
    json.dumps(summary, allow_nan=False)
    return {
        "summary": summary,
        "enrollment_by_year": yearly.rename("enroll_ftug").reset_index(),
        "state_results": state.reset_index(),
    }


def make_latex_macros(summary):
    """Format only at the presentation boundary. Macros contain no currency units."""
    definitions = summary["definitions"]
    enrollment = summary["enrollment"]
    budget = summary["budget"]
    macros = {
        "StudyStartYear": str(definitions["start_year"]),
        "StudyEndYear": str(definitions["end_year"]),
        "AidAcademicYear": f'{definitions["aid_year"]}--{(definitions["aid_year"] + 1) % 100:02d}',
        "PanelInstitutions": f'{summary["sample"]["institutions"]:,}',
        "PanelRows": f'{summary["sample"]["institution_years"]:,}',
        "PanelStates": str(summary["sample"]["states_in_aid_year"]),
        "EnrollmentStart": f'{enrollment["start"]:,.0f}',
        "EnrollmentEnd": f'{enrollment["end"]:,.0f}',
        "EnrollmentChangePct": f'{enrollment["change_percent"]:.2f}',
        "NYAid": f'{summary["ny_vt"]["NY"]:,.2f}',
        "VTAid": f'{summary["ny_vt"]["VT"]:,.2f}',
        "NYMinusVTAid": f'{summary["ny_vt"]["NY_minus_VT"]:,.2f}',
        "CurrentBudget": f'{budget["current_total"]:,.2f}',
        "SimulatedBudget": f'{budget["simulated_total"]:,.2f}',
        "BudgetChangeDollars": f'{budget["change"]:,.2f}',
        "BudgetChangeMillions": f'{budget["change"] / 1_000_000:,.1f}',
        "StatesNetIncrease": str(budget["states_net_increase"]),
        "StatesNetDecrease": str(budget["states_net_decrease"]),
        "StatesUnchanged": str(budget["states_unchanged"]),
    }
    stat_names = {
        "mean": "Mean", "median": "Median", "std": "SD", "min": "Min",
        "max": "Max", "range": "Range", "p10": "PTen", "p25": "PTwentyFive",
        "p75": "PSeventyFive", "p90": "PNinety", "ratio_90_10": "Ratio",
    }
    for system, prefix in (("current", "CurrentAid"), ("simulated", "SimulatedAid")):
        for key, suffix in stat_names.items():
            macros[prefix + suffix] = f'{summary[system][key]:,.2f}'
    lines = [
        "% AUTO-GENERATED by script/plot.py. Do not edit by hand.",
        "% Values below are presentation strings; analysis_results.json stores numbers.",
        "% Currency symbols and percent signs belong in ED_memo.tex, not these macros.",
    ]
    lines += [f"\\newcommand{{\\{name}}}{{{value}}}" for name, value in macros.items()]
    return "\n".join(lines) + "\n"


def _atomic_text(path, text):
    """Replace one completed file; this is not a multi-file transaction."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_results(results, results_dir, tex_path, *, input_file=None):
    """Export JSON, two CSV tables, and linked LaTeX macros from the same object.

    The caller should invoke this after successful figure generation. Serializing
    all content before writing avoids publishing invalid JSON or incomplete macros.
    """
    metadata = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(),
        "pandas_version": pd.__version__, "numpy_version": np.__version__,
    }
    if input_file is not None:
        path = Path(input_file)
        with path.open("rb") as handle:
            metadata["input_sha256"] = hashlib.file_digest(handle, "sha256").hexdigest()
        metadata["input_filename"] = path.name
    payload = {
        "metadata": metadata,
        "summary": results["summary"],
        "enrollment_by_year": results["enrollment_by_year"].to_dict(orient="records"),
        "state_results": results["state_results"].to_dict(orient="records"),
    }
    root = Path(results_dir)
    outputs = {
        root / "analysis_results.json": json.dumps(payload, indent=2, allow_nan=False) + "\n",
        root / "enrollment_by_year.csv": results["enrollment_by_year"].to_csv(index=False),
        root / "state_results.csv": results["state_results"].to_csv(index=False),
        Path(tex_path): make_latex_macros(results["summary"]),
    }
    # Publish the LaTeX bridge last; never populate it with synthetic placeholders.
    for path, text in outputs.items():
        _atomic_text(path, text)
        print(f"Results saved to: {path}")
    return list(outputs)
