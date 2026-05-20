import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import zipfile

load_dotenv()

base_path = os.getenv("BASE_DOWNLOAD_PATH")
hd_url_template = os.getenv("NCES_HD_URL_TEMPLATE")
flags_url_template = os.getenv("NCES_FLAGS_URL_TEMPLATE")

if not all([base_path, hd_url_template, flags_url_template]):
    raise ValueError("Missing configuration. Please check your .env file.")

download_folder = input("Download directory name: ")
download_dir = os.path.join(base_path, download_folder)
os.makedirs(download_dir, exist_ok=True)
extracted_folder = input("Extract directory name: ")
extract_dir = os.path.join(base_path, extracted_folder)
os.makedirs(extract_dir, exist_ok=True)


start_year = int(input("Starting year: "))
end_year = int(input("Ending year: "))

def download_file(download_info):
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

tasks = []
for year in range(start_year, end_year + 1):
    hd_url = hd_url_template.format(year)
    flags_url = flags_url_template.format(year)
    tasks.extend([
        (hd_url, os.path.join(download_dir, f'HD{year}.zip')),
        (flags_url, os.path.join(download_dir, f'FLAGS{year}.zip'))
    ])

print(f"Queued {len(tasks)} files for download...")

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [executor.submit(download_file, task) for task in tasks]
    
    for future in as_completed(futures):
        print(future.result())

print("All downloads complete.\n\n--- Starting Extraction ---")

# 2. Loop through the same 'tasks' list we used for downloading
for url, file_path in tasks:
    # 3. Verify the file actually exists (in case a download failed earlier)
    if os.path.exists(file_path):
        filename = os.path.basename(file_path)
        print(f"Extracting {filename}...")
        
        try:
            # 4. Open the ZIP and extract all contents to our new folder
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
        except zipfile.BadZipFile:
            print(f"Error: {filename} is corrupted or not a valid ZIP file.")
    else:
        print(f"Skipping {file_path} (File not found).")

print(f"\nAll files successfully extracted to: {extract_dir}")