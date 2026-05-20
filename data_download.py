import os
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()

base_path = os.getenv("BASE_DOWNLOAD_PATH")
hd_url_template = os.getenv("NCES_HD_URL_TEMPLATE")
flags_url_template = os.getenv("NCES_FLAGS_URL_TEMPLATE")

if not all([base_path, hd_url_template, flags_url_template]):
    raise ValueError("Missing configuration. Please check your .env file.")

user_folder = input("Download directory name: ")
download_dir = os.path.join(base_path, user_folder)
os.makedirs(download_dir, exist_ok=True)

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

print("All downloads complete.")