# ED_data

Analysis pipeline for 2-Year Public College Enrollment Trends and Federal Grant Allocations using IPEDS data.

## Repository Structure

* **`data/`**: The data vault. 
  * `raw/`: Untouched, original IPEDS downloads (read-only).
  * `interim/`: Processing files.
  * `clean/`: Processed `.parquet` files ready for analysis and csv ready for sharing.
* **`scripts/`**: Containing all Python script.
* **`figures/`**: The generated output, including `.png` charts and the final PDF memo.

## Quick Start
Initialize the environment:
```
pip3 install -r requirements.txt
```
Replace the placeholders in the .env file with the data path and URL you would like to work with.

Download the raw data:
```
python3 data_download.py
```
Clean and process the dataset:
```
python3 data_clean.py
```
Generate the analysis figures:
```
python3 plot.py
```