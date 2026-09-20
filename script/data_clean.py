import os
import pandas as pd
from dotenv import load_dotenv
import argparse  

def parse_args():  # Define the command-line options and defaults.
    parser = argparse.ArgumentParser(  
        description="Process annual IPEDS data files."  
    )  

    parser.add_argument(  # Allow users to override the first academic year.
        "--start-year", type=int, default=2010,  
        help="First academic year to process (default: 2010)"  
    )  

    parser.add_argument(  # Allow users to override the last academic year.
        "--end-year", type=int, default=2015, 
        help="Last academic year to process (default: 2015)"  
    )  

    parser.add_argument(  # Allow users to override the folder for extracted CSV files.
        "--interim-dir", default="data/interim",  
        help="Directory of extracted files (default: data/interim)"  
    )  

    parser.add_argument(  # Allow users to override the folder for processed files.
        "--cleaned-dir", default="data/cleaned",  
        help="Directory for processed files (default: data/cleaned)"  
    )  

    args = parser.parse_args()  
    if args.start_year > args.end_year:  # Reject a reversed year range before processing files.
        parser.error("--start-year must be less than or equal to --end-year")  
    return args  

def process_ipeds_data(extract_dir, start_year, end_year):
    """
    Reads, merges, and cleans IPEDS HD and SFA datasets across multiple years.
    Returns a single balanced panel dataframe.
    """
    print("\n--- Step 1: Combining Datasets ---")
    all_years_data = []
    hd_columns = [
            "UNITID",
            "STABBR",
            "UGOFFER",
            "CONTROL",
            "ICLEVEL"
        ]
    sfa_columns = [
            "UNITID",
            "SCUGFFN",
            "FGRNT_T"
        ]

    for year in range(start_year, end_year + 1):
        academic_yr = f"{year % 100:02d}{(year + 1) % 100:02d}"
        
        hd_file = os.path.join(extract_dir, f'HD{year}.csv')
        sfa_file = os.path.join(extract_dir, f'SFA{academic_yr}.csv')

        if not os.path.exists(hd_file):
            raise FileNotFoundError(f"Missing HD file: {hd_file}")

        if not os.path.exists(sfa_file):
            raise FileNotFoundError(f"Missing SFA file: {sfa_file}")

        df_hd = pd.read_csv(hd_file, encoding="cp1252", low_memory=False, usecols=hd_columns)
        df_sfa = pd.read_csv(sfa_file, encoding="cp1252", low_memory=False, usecols=sfa_columns)
        df_hd["UNITID"] = df_hd["UNITID"].astype(str).str.strip()
        df_sfa["UNITID"] = df_sfa["UNITID"].astype(str).str.strip()

        df_merged = (pd.merge(
            df_hd,
            df_sfa,
            on="UNITID",
            how="left",
            validate="one_to_one",
            ).assign(YEAR=year))

        all_years_data.append(df_merged)

    # Finalize the master dataset
    print("\nStacking all years into final_df...")
    final_df = pd.concat(all_years_data, ignore_index=True)
    print(f"Combined Data Shape: {final_df.shape[0]} rows, {final_df.shape[1]} columns.")

    print("\n--- Applying Filtering Logic ---")

    # Delete out of scope states by filtering stabbr
    # Keep only institutions that offer undergraduate programs
    territories_to_drop = ['DC', 'FM', 'MH', 'MP', 'PR', 'PW', 'VI', 'GU', 'AS']
    final_df = final_df.loc[(~final_df["STABBR"].isin(territories_to_drop)) & (final_df["UGOFFER"] == 1)].copy()

    # Assignment definition: "two-year college" = undergraduate institution that does not grant bachelor's degrees.
    # Create dummy variables

    final_df["PUBLIC"] = (final_df["CONTROL"] == 1).astype(int)
    final_df["DEGREE_BACH"] = (final_df["ICLEVEL"] == 1).astype(int)

    # Keep only columns we need
    columns_to_keep = [
        'UNITID',       
        'STABBR',       
        'YEAR',         
        'PUBLIC',       
        'DEGREE_BACH',        
        'SCUGFFN',      
        'FGRNT_T'       
    ]

    #Makes sure we have all the columns as exepected
    missing = set(columns_to_keep) - set(final_df.columns)
    if missing:
        raise ValueError(f"Missing required variables: {missing}")

    clean_panel_df = final_df[columns_to_keep].copy()

    print("\n--- Creating a Balanced Panel ---")

    # Drop rows with missing values
    clean_panel_df = clean_panel_df.dropna(subset=columns_to_keep)

    # Retain institutions observed in every requested year
    if clean_panel_df.duplicated(["UNITID", "YEAR"]).any():
        raise ValueError("Duplicate institution-year observations detected.")
    year_counts = (clean_panel_df.groupby("UNITID")["YEAR"].nunique())
    expected_years = end_year - start_year + 1
    valid_schools = year_counts[year_counts == expected_years].index
    
    # Filter the dataframe to only keep rows where the school ID is in that valid list
    clean_panel_df = (
        clean_panel_df.loc[
        clean_panel_df["UNITID"].isin(valid_schools)
        ]
        .copy()
        .rename(columns={
            "UNITID": "ID_IPEDS",
            "STABBR": "stabbr",
            "YEAR": "year",
            "DEGREE_BACH": "degree_bach",
            "PUBLIC": "public",
            "SCUGFFN": "enroll_ftug",
            "FGRNT_T": "grant_federal",
        })
    )

    print(f"Balanced panel created. Final size: {clean_panel_df.shape[0]} rows.")
    
    return clean_panel_df
    
def main():

    args = parse_args()  
    load_dotenv()
    base_path = os.getenv("BASE_PROJECT_PATH", ".")

    interim_dir = os.path.join(base_path, args.interim_dir)
    os.makedirs(interim_dir, exist_ok=True)

    clean_dir = os.path.join(base_path, args.cleaned_dir)
    os.makedirs(clean_dir, exist_ok=True)
    
    clean_data = process_ipeds_data(interim_dir, args.start_year, args.end_year)

    if clean_data.empty:
        raise ValueError("No institutions satisfy the balanced-panel requirements.")

    csv_path = os.path.join(clean_dir, "cleaned_panel.csv")
    parquet_path = os.path.join(clean_dir, "cleaned_panel.parquet")
        
    clean_data.to_csv(csv_path, index=False)
    clean_data.to_parquet(parquet_path, index=False)
        
    print("\n--- Export Complete ---")
    print(f"CSV saved to: {csv_path}")
    print(f"Parquet saved to: {parquet_path}")
    
if __name__ == "__main__":
    main()