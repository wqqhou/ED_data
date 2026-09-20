import argparse  
import os
import requests
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

def parse_args():  # Define the command-line options and defaults.
    parser = argparse.ArgumentParser(  
        description="Download annual IPEDS data files."  
    )  

    parser.add_argument(  # Allow users to override the first academic year.
        "--start-year", type=int, default=2010,  
        help="First academic year to download (default: 2010)"  
    )  

    parser.add_argument(  # Allow users to override the last academic year.
        "--end-year", type=int, default=2015, 
        help="Last academic year to download (default: 2015)"  
    )  

    parser.add_argument(  # Allow users to override the folder for downloaded ZIP files.
        "--download-dir", default="data/raw",  
        help="Directory for downloaded files (default: data/raw)"  
    )  

    parser.add_argument(  # Allow users to override the folder for extracted CSV files.
        "--extract-dir", default="data/interim",  
        help="Directory for extracted files (default: data/interim)"  
    )  

    args = parser.parse_args()  
    if args.start_year > args.end_year:  # Reject a reversed range before downloading any files.
        parser.error("--start-year must be less than or equal to --end-year")  
    return args  

def download_file(download_info):
    """
    Downloads a file in chunks given a tuple of (url, file_path).
    Returns a success or failure message.
    """
    url, file_path = download_info
    print(f"Started downloading: {url}")
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(file_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
                    
        return f"Successfully saved: {file_path}"
    
    except requests.exceptions.RequestException as e:
        return f"Failed to download {url}. Error: {e}"

def main():
    # Load configuration, download files concurrently, and extract them using command-line options.
    args = parse_args()  
    load_dotenv()
    
    base_path = os.getenv("BASE_PROJECT_PATH")
    hd_url_template = os.getenv("NCES_HD_URL_TEMPLATE")
    sfa_url_template = os.getenv("NCES_SFA_URL_TEMPLATE")
    
    if not all([base_path, hd_url_template, sfa_url_template]):
        raise ValueError("Missing configuration. Please check your .env file.")
        
    # Resolve the selected directories relative to BASE_PROJECT_PATH; absolute paths also work.
    download_dir = os.path.join(base_path, args.download_dir)  
    os.makedirs(download_dir, exist_ok=True)
    
    extract_dir = os.path.join(base_path, args.extract_dir)  
    os.makedirs(extract_dir, exist_ok=True)
    
    start_year = args.start_year  
    end_year = args.end_year  
    
    # Setup Concurrent Downloading Workflow
    tasks = []
    for year in range(start_year, end_year + 1):
        academic_yr = f"{year % 100:02d}{(year + 1) % 100:02d}"
        hd_url = hd_url_template.format(year)
        sfa_url = sfa_url_template.format(academic_yr)
        
        tasks.extend([
            (hd_url, os.path.join(download_dir, f'HD{year}.zip')),
            (sfa_url, os.path.join(download_dir, f'SFA{academic_yr}.zip'))
        ])
        
    print(f"\nQueued {len(tasks)} files for download...")
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(download_file, task) for task in tasks]
        
        for future in as_completed(futures):
            print(future.result())
            
    print("All downloads complete.\n\n--- Starting Extraction ---")
    
    # Extract Downloaded Files
    for url, file_path in tasks:
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            print(f"Extracting {filename}...")
            try:
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    all_files = zip_ref.namelist()
                    files_to_keep = [f for f in all_files if not f.lower().endswith('_rv.csv')]

                    for target_file in files_to_keep:
                        zip_ref.extract(target_file, extract_dir)

            except zipfile.BadZipFile:
                print(f"Error: {filename} is corrupted or not a valid ZIP file.")
        else:
            print(f"Skipping {file_path} (File not found).")
            
    print(f"\nAll files successfully extracted to: {extract_dir}")

if __name__ == "__main__":
    main()  