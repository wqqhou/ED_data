"""Build a complete-case IPEDS panel with value checks and sample accounting."""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# The study includes the 50 states, excluding the other areas listed below.
US_STATES = set(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA "
    "WV WI WY".split()
)
EXCLUDED_AREAS = {"DC", "FM", "MH", "MP", "PR", "PW", "VI", "GU", "AS"}


def reject_invalid_rows(df, invalid, message, columns):
    """Stop with a count and example records, rather than silently dropping errors."""
    invalid = invalid.fillna(False)
    if invalid.any():
        identifiers = [c for c in ("UNITID", "YEAR") if c in df.columns]
        display_columns = list(dict.fromkeys(identifiers + list(columns)))
        examples = df.loc[invalid, display_columns].head(5)
        raise ValueError(
            f"{message}: {int(invalid.sum()):,} row(s).\n"
            f"Examples:\n{examples.to_string(index=False)}"
        )


def validate_values(df):
    """Validate in-scope observations after imputation masking.

    Missing quantitative values remain missing for the later complete-case filter.
    Observed amounts/counts must be numeric, finite, and nonnegative; enrollment
    must also be a whole-number count. Zero enrollment is not deleted here.
    """
    df = df.copy()

    for column in ("SCUGFFN", "FGRNT_T"):
        original = df[column]
        numeric = pd.to_numeric(original, errors="coerce")

        # Coercion is diagnostic only: do not silently turn bad text into missingness.
        bad_text = original.notna() & numeric.isna()
        reject_invalid_rows(df, bad_text, f"Non-numeric {column}", [column])

        values = numeric.to_numpy(dtype=float, na_value=np.nan)
        bad_value = numeric.notna() & (~np.isfinite(values) | (values < 0))
        reject_invalid_rows(
            df, bad_value, f"Negative or infinite {column}", [column]
        )

        if column == "SCUGFFN":
            fractional = numeric.notna() & numeric.mod(1).ne(0)
            reject_invalid_rows(
                df, fractional, "Enrollment must be a whole-number count", [column]
            )

        df[column] = numeric

    return df


def parse_args():
    parser = argparse.ArgumentParser(description="Process annual IPEDS data files.")
    parser.add_argument("--start-year", type=int, default=2010,
                        help="First academic year to process (default: 2010)")
    parser.add_argument("--end-year", type=int, default=2015,
                        help="Last academic year to process (default: 2015)")
    parser.add_argument("--interim-dir", default="data/interim",
                        help="Directory of extracted files (default: data/interim)")
    parser.add_argument("--cleaned-dir", default="data/cleaned",
                        help="Directory for processed files (default: data/cleaned)")
    args = parser.parse_args()
    if args.start_year > args.end_year:
        parser.error("--start-year must be less than or equal to --end-year")
    return args


def process_ipeds_data(extract_dir, start_year, end_year, *, audit_path=None):
    """Read annual files and return a balanced panel; optionally save sample attrition."""
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    all_years_data = []
    audit_rows = []
    years = range(start_year, end_year + 1)
    hd_columns = ["UNITID", "STABBR", "UGOFFER", "CONTROL", "ICLEVEL"]
    sfa_columns = ["UNITID", "SCUGFFN", "FGRNT_T", "XSCUGFFN", "XFGRNT_T"]

    def record_sample(step, stage, df):
        # Include zero counts for years with no remaining observations.
        for year in years:
            part = df.loc[df["YEAR"].eq(year)]
            audit_rows.append({
                "step": step, "stage": stage, "year": year,
                "rows": len(part), "institutions": part["UNITID"].nunique(),
            })

    print("\n--- Step 1: Combining Datasets ---")
    for year in years:
        academic_yr = f"{year % 100:02d}{(year + 1) % 100:02d}"
        hd_file = Path(extract_dir) / f"HD{year}.csv"
        sfa_file = Path(extract_dir) / f"SFA{academic_yr}.csv"
        if not hd_file.exists():
            raise FileNotFoundError(f"Missing HD file: {hd_file}")
        if not sfa_file.exists():
            raise FileNotFoundError(f"Missing SFA file: {sfa_file}")

        # Preserve identifier missingness and avoid numeric-to-string artifacts.
        df_hd = pd.read_csv(hd_file, encoding="cp1252", low_memory=False, usecols=hd_columns, dtype={"UNITID": "string"})
        df_sfa = pd.read_csv(sfa_file, encoding="cp1252", low_memory=False, usecols=sfa_columns, dtype={"UNITID": "string"})
        
        for frame, source in ((df_hd, hd_file), (df_sfa, sfa_file)):
            frame["UNITID"] = frame["UNITID"].str.strip()
            bad_id = frame["UNITID"].isna() | frame["UNITID"].eq("")
            reject_invalid_rows(frame, bad_id, f"Missing UNITID in {source}", ["UNITID"])

        df_merged = pd.merge(
            df_hd, df_sfa, on="UNITID", how="left", validate="one_to_one", indicator="_sfa_match",
        ).assign(YEAR=year)

        all_years_data.append(df_merged)

        # The left merge does not retain SFA-only rows; disclose that count as well.
        sfa_only = (~df_sfa["UNITID"].isin(df_hd["UNITID"])).sum()
        print(f"{year}: SFA institutions without an HD match = {int(sfa_only):,}")

    final_df = pd.concat(all_years_data, ignore_index=True)
    record_sample(0, "HD observations before requiring an SFA match", final_df)

    # Unmatched HD rows would otherwise be removed later for missing SFA values.
    final_df = final_df.loc[final_df["_sfa_match"].eq("both")].copy()
    record_sample(1, "HD-SFA matched observations", final_df)
    # Normalize classification codes before comparing them with numeric codes.
    # Unparseable entries become missing and are excluded by the existing filters.
    for column in ("UGOFFER", "CONTROL", "ICLEVEL"):
        final_df[column] = pd.to_numeric(final_df[column], errors="coerce")

    print("\n--- Applying Filtering Logic ---")

    imputed_codes = {"J", "L", "N", "P"}
    flag_columns = {"SCUGFFN": "XSCUGFFN", "FGRNT_T": "XFGRNT_T"}
    for value_col, flag_col in flag_columns.items():
        flags = final_df[flag_col].astype("string").str.strip().str.upper()
        is_imputed = flags.isin(imputed_codes)
        n_replaced = (is_imputed & final_df[value_col].notna()).sum()
        final_df.loc[is_imputed, value_col] = np.nan
        print(f"{value_col}: set {int(n_replaced):,} imputed values to missing")

    # Validate geography before applying the study's exclusion list.
    final_df["STABBR"] = (final_df["STABBR"].astype("string").str.strip().str.upper().replace("", pd.NA))
    unknown_state = (final_df["STABBR"].notna() & ~final_df["STABBR"].isin(US_STATES | EXCLUDED_AREAS))
    reject_invalid_rows(final_df, unknown_state, "Unrecognized STABBR", ["STABBR"])
    in_scope = (~final_df["STABBR"].isin(EXCLUDED_AREAS) & final_df["UGOFFER"].eq(1))
    final_df = final_df.loc[in_scope].copy()
    record_sample(2, "Geographic and undergraduate scope", final_df)

    # Exclusion of missing or invalid classifications.
    valid_classifications = (
        final_df["CONTROL"].isin([1, 2, 3])
        & final_df["ICLEVEL"].isin([1, 2, 3])
    )

    final_df = final_df.loc[valid_classifications].copy()
    record_sample(3, "Valid CONTROL and ICLEVEL", final_df)

    # Validate observed quantities only for the sample eligible for analysis.
    final_df = validate_values(final_df)
    final_df["PUBLIC"] = final_df["CONTROL"].eq(1).astype(int)
    # Preserve the original proxy for bachelor's-degree-granting status.
    final_df["DEGREE_BACH"] = final_df["ICLEVEL"].eq(1).astype(int)

    columns_to_keep = [
        "UNITID", "STABBR", "YEAR", "PUBLIC", "DEGREE_BACH", "SCUGFFN", "FGRNT_T"
    ]
    clean_panel_df = final_df[columns_to_keep].dropna(subset=columns_to_keep).copy()
    record_sample(4, "Complete cases after imputation masking", clean_panel_df)

    if clean_panel_df.duplicated(["UNITID", "YEAR"]).any():
        raise ValueError("Duplicate institution-year observations detected.")
    year_counts = clean_panel_df.groupby("UNITID")["YEAR"].nunique()
    expected_years = end_year - start_year + 1
    valid_schools = year_counts[year_counts.eq(expected_years)].index
    clean_panel_df = clean_panel_df.loc[
        clean_panel_df["UNITID"].isin(valid_schools)
    ].copy()
    record_sample(5, "Balanced panel", clean_panel_df)

    audit = pd.DataFrame(audit_rows).sort_values(["step", "year"])
    for column in ("rows", "institutions"):
        audit[f"{column}_removed"] = (
            -audit.groupby("year")[column].diff()
        ).fillna(0).astype(int)
    print("\n--- Sample construction by year ---")
    print(audit.to_string(index=False))
    if audit_path is not None:
        audit_path = Path(audit_path)
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        audit.to_csv(audit_path, index=False)
        print(f"Sample audit saved to: {audit_path}")

    clean_panel_df = clean_panel_df.rename(columns={
        "UNITID": "ID_IPEDS", "STABBR": "stabbr", "YEAR": "year",
        "DEGREE_BACH": "degree_bach", "PUBLIC": "public",
        "SCUGFFN": "enroll_ftug", "FGRNT_T": "grant_federal",
    })
    print(f"Balanced panel created. Final size: {len(clean_panel_df):,} rows.")
    return clean_panel_df


def main():
    args = parse_args()
    load_dotenv()
    repo_root = Path(__file__).resolve().parents[1]
    base_path = Path(os.getenv("BASE_PROJECT_PATH", repo_root)).expanduser().resolve()
    interim_dir = base_path / args.interim_dir
    clean_dir = base_path / args.cleaned_dir
    clean_dir.mkdir(parents=True, exist_ok=True)

    clean_data = process_ipeds_data(
        interim_dir, args.start_year, args.end_year,
        audit_path=clean_dir / "sample_audit.csv",
    )
    if clean_data.empty:
        raise ValueError("No institutions satisfy the balanced-panel requirements.")

    csv_path = clean_dir / "cleaned_panel.csv"
    parquet_path = clean_dir / "cleaned_panel.parquet"
    clean_data.to_csv(csv_path, index=False)
    clean_data.to_parquet(parquet_path, index=False)
    print(f"\nCSV saved to: {csv_path}")
    print(f"Parquet saved to: {parquet_path}")


if __name__ == "__main__":
    main()
