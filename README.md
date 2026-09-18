# ED_data

Analysis pipeline for 2-Year Public College Enrollment Trends and Federal Grant Allocations using IPEDS data.

## Repository Structure

* **`data/`**: The data vault. 
  * `raw/`: Untouched, original IPEDS downloads (read-only).
  * `interim/`: Processing files.
  * `clean/`: Processed `.parquet` files ready for analysis and csv ready for sharing.
* **`scripts/`**: Containing all Python script.
 * **`Figure/`**: Containing all output figures.

## Research workflow

- Downloads annual IPEDS Institutional Characteristics (HD) and Student Financial Aid (SFA) files programmatically and in parallel.
- Merges institution-level files by `UNITID`, standardizes fields, applies sample restrictions, and constructs a balanced six-year panel.
- Measures enrollment changes among public two-year institutions and compares per-student federal aid across states.
- Computes state-level distributional statistics, including percentiles and 90/10 ratios, and produces U.S. choropleth maps.
- Implements a counterfactual grant-allocation formula and evaluates its distributional and budget implications, including state-level gains and losses.

## Methods and tools

**Python, pandas, Requests, concurrent downloads, Parquet, Matplotlib, Seaborn, Plotly, descriptive statistics, policy simulation**

The repository separates data acquisition, cleaning, analysis, and visualization into reproducible scripts and includes the resulting figures and research memo.

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
