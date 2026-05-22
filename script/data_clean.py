import os
import pandas as pd
import numpy as numpy
from dotenv import load_dotenv




def process_ipeds_data(extract_dir, start_year, end_year):
    """
    Reads, merges, and cleans IPEDS HD and SFA datasets across multiple years.
    Returns a single, perfectly balanced panel dataframe.
    """
    print("\n--- Step 1: Combining Datasets ---")
    all_years_data = []

    for year in range(start_year, end_year + 1):
        academic_yr = f"{year % 100:02d}{(year + 1) % 100:02d}"
        
        hd_file = os.path.join(extract_dir, f'HD{year}.csv')
        sfa_file = os.path.join(extract_dir, f'SFA{academic_yr}.csv')

        if os.path.exists(hd_file) and os.path.exists(sfa_file):
            print(f"Reading and merging data for {year}...")
            
            df_hd = pd.read_csv(hd_file, encoding='cp1252', low_memory=False)
            df_sfa = pd.read_csv(sfa_file, encoding='cp1252', low_memory=False)

            # Preventative formatting
            df_hd.columns = df_hd.columns.str.upper().str.strip()
            df_sfa.columns = df_sfa.columns.str.upper().str.strip()
            df_hd['UNITID'] = df_hd['UNITID'].astype(str).str.strip()
            df_sfa['UNITID'] = df_sfa['UNITID'].astype(str).str.strip()

            # Combine the SFA and HD files by school ID
            df_merged = pd.merge(df_hd, df_sfa, on='UNITID', how='left')

            # Include year label in the dataset
            df_merged['YEAR'] = year

            # Combine the annual dataset into the master list
            all_years_data.append(df_merged)
        else:
            print(f"Warning: Missing files for {year}. Skipping.")

    # Finalize the master dataset
    print("\nStacking all years into final_df...")
    final_df = pd.concat(all_years_data, ignore_index=True)
    print(f"Combined Data Shape: {final_df.shape[0]} rows, {final_df.shape[1]} columns.")

    print("\n--- Applying Filtering Logic ---")

    # Delete out of scope states by filtering stabbr
    territories_to_drop = ['DC', 'FM', 'MH', 'MP', 'PR', 'PW', 'VI', 'GU', 'AS']
    final_df = final_df[~final_df['STABBR'].isin(territories_to_drop)]

    # Keep only institutions that offer undergraduate programs
    final_df = final_df[final_df['UGOFFER'] == 1]

    # Create dummy variables
    final_df['PUBLIC'] = (final_df['CONTROL'] == 1).astype(int)
    final_df['DEGREE_BACH'] = (final_df['ICLEVEL'] == 1).astype(int)

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

    available_columns = [col for col in columns_to_keep if col in final_df.columns]
    clean_panel_df = final_df[available_columns].copy()

    print("\n--- Creating a Balanced Panel ---")

    # Drop rows with missing values
    clean_panel_df = clean_panel_df.dropna()
    # Enforce exactly 6 years of data per school
    school_counts = clean_panel_df['UNITID'].value_counts()
    valid_schools = school_counts[school_counts == 6].index
    # Filter the dataframe to only keep rows where the school ID is in that valid list
    clean_panel_df = clean_panel_df[clean_panel_df['UNITID'].isin(valid_schools)]
    clean_panel_df.rename(columns={
        'UNITID': 'ID_IPEDS',
        'STABBR': 'stabbr',
        'YEAR': 'year',
        'DEGREE_BACH': 'degree_bach',
        'PUBLIC': 'public',
        'SCUGFFN': 'enroll_ftug',
        'FGRNT_T': 'grant_federal'
    }, inplace=True)

    print(f"Balanced panel created. Final size: {clean_panel_df.shape[0]} rows.")
    
    return clean_panel_df


def main():

    load_dotenv()
    base_path = os.getenv("BASE_PROJECT_PATH")

    interim_folder = input("Interim Directory name:")
    interim_dir = os.path.join(base_path, interim_folder)
    os.makedirs(interim_dir, exist_ok=True)

    clean_folder = input("Interim Clean name:")
    clean_dir = os.path.join(base_path, clean_folder)
    os.makedirs(clean_dir, exist_ok=True)
    
    clean_data = process_ipeds_data(interim_dir, 2010, 2015)
    
    if clean_data is not None and not clean_data.empty:
        csv_path = os.path.join(clean_dir, "cleaned_panel.csv")
        parquet_path = os.path.join(clean_dir, "cleaned_panel.parquet")
        
        clean_data.to_csv(csv_path, index=False)
        clean_data.to_parquet(parquet_path, index=False)
        
        print("\n--- Export Complete ---")
        print(f"CSV saved to: {csv_path}")
        print(f"Parquet saved to: {parquet_path}")
    else:
        print("\nError: Data processing failed or resulted in an empty dataframe. Nothing saved.")

if __name__ == "__main__":
    main()