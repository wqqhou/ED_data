# ED Data Analysis: College Enrollment & Federal Grant Allocation

Independent empirical data-analysis project using the **Integrated Postsecondary Education Data System (IPEDS)** to study enrollment trends and the geographic distribution of federal student aid.

**Context:** This repository contains my independent solution to a faculty-assigned data analysis task provided by **Prof. Anran Li**. The task was framed as a policy analysis for the U.S. Department of Education (ED).

The assignment specified the research questions, sample definitions, and counterfactual policy formula described below. I independently completed the **data acquisition, cleaning, panel construction, statistical analysis, policy simulation, visualizations, and policy memo in Python**.

---

## Assignment Specification

### 1. Construct an IPEDS Panel

The first task was to construct an institution-level panel using two components of IPEDS:

* **Directory Information (HD)** from the Institutional Characteristics survey
* **Student Financial Aid and Net Price (SFA)** files

The requested panel covers academic years **2010-11 through 2015-16** and contains:

| Variable        | Description                                                             |
| --------------- | ----------------------------------------------------------------------- |
| `ID_IPEDS`      | Unique institution identifier                                           |
| `stabbr`        | Two-letter state abbreviation                                           |
| `year`          | Academic year, coded by starting year                                   |
| `degree_bach`   | Indicator for bachelor's-degree-granting institution                    |
| `public`        | Indicator for public institution                                        |
| `enroll_ftug`   | First-time, full-time undergraduate enrollment                          |
| `grant_federal` | Total federal grant aid awarded to first-time, full-time undergraduates |

The assignment additionally required that I:

* construct a **balanced six-year panel**, retaining only institutions observed in every year;
* exclude Washington, D.C. and U.S. territories;
* restrict the sample to institutions offering undergraduate education;
* retain both public and private institutions in the master panel;
* use IPEDS total-count variables rather than manually summing subcategories;
* use the original reported IPEDS data rather than revised or imputed values; and
* conduct all data analysis in **Python**.

---

## Research Questions

### A. Enrollment Trends

For this exercise, the assignment defined a **"two-year college"** as:

> an undergraduate institution that does not grant bachelor's degrees.

Using this definition, I was asked to determine whether total first-time, full-time enrollment at **public two-year colleges** increased, decreased, or remained approximately constant between 2010-11 and 2015-16.

The analysis was also required to discuss limitations arising from the construction of the balanced panel.

### B. Federal Grant Distribution

Using only the **2015-16** data, I was asked to evaluate the geographic distribution of federal grant aid.

The analysis addressed three questions:

1. **New York vs. Vermont:** Assess Vermont's claim that neighboring New York receives substantially greater federal grant aid on a per-student basis.

2. **Cross-state dispersion:** Calculate summary statistics describing the spread of average per-student federal grant aid across states and interpret what those statistics imply.

3. **Counterfactual allocation:** Simulate a proposed school-level federal grant formula based on enrollment:

$$\text{Federal Grant}_i=1750 \times \text{Enrollment}_i+0.15 \times \text{Enrollment}_i^2$$

and evaluate how the counterfactual changes the **cross-state dispersion of average per-student federal grant aid**.

The definition of a two-year college and the counterfactual grant formula were supplied as part of the assignment rather than chosen independently.

---

## Implementation

The project separates the empirical workflow into three stages.

### 1. Data Acquisition — `script/data_download.py`

* Programmatically downloads annual IPEDS HD and SFA files from NCES.
* Uses concurrent downloads to retrieve annual files efficiently.
* Extracts the original CSV data.
* Excludes revised (`_rv`) files.
* Allows the starting and ending academic years to be configured at runtime.

### 2. Panel Construction — `script/data_clean.py`

* Reads and standardizes annual HD and SFA files.
* Merges the two surveys by institution identifier (`UNITID`).
* Constructs the requested public and bachelor's-degree indicators.
* Applies the geographic and undergraduate-institution restrictions.
* Retains the variables required by the assignment.
* Stacks annual observations into an institution-year panel.
* Restricts the final dataset to institutions with complete observations throughout the six-year period.
* Exports the resulting panel in both CSV and Parquet formats.

### 3. Analysis & Policy Simulation — `script/plot.py`

The analysis script:

* calculates aggregate enrollment trends for public two-year institutions;
* compares federal grant aid per student in New York and Vermont;
* aggregates federal grant aid and enrollment to the state level;
* calculates measures of cross-state dispersion, including percentiles, standard deviation, and the 90/10 ratio;
* generates geographic visualizations of state-level aid;
* implements the specified counterfactual federal grant formula;
* compares the observed and simulated distributions of per-student aid; and
* calculates the implied federal budget change and state-level gains/losses under the counterfactual.

---

## Selected Results

The submitted analysis finds that:

* First-time, full-time undergraduate enrollment at public two-year colleges in the balanced panel **declined by 16.65% between 2010 and 2015**.
* Considerable cross-state variation in average federal grant aid per student is present in the 2015-16 data.
* Under the specified counterfactual allocation formula, the cross-state distribution becomes substantially less dispersed:

  * the **90/10 ratio declines from 1.63 to 1.12**;
  * the difference between the highest- and lowest-aid states declines from approximately **$1,629 to $711 per student**; and
  * the cross-state standard deviation falls substantially.
* The simulated allocation would require approximately **$133.3 million in additional federal grant expenditure** relative to the observed allocation.

These results should be interpreted as a descriptive and counterfactual exercise under the definitions and allocation rule specified in the original task.

---

## Repository Structure

```text
ED_data/
│
├── script/
│   ├── main.py              # Run the complete download, clean, and plot workflow
│   ├── cli.py               # Shared command-line arguments and directory defaults
│   ├── data_download.py     # Download and extract annual IPEDS files
│   ├── data_clean.py        # Merge, clean, and construct balanced panel
│   └── plot.py              # Statistical analysis, simulation, and figures
│
├── figure/
│   ├── ED_memo.pdf
│   ├── figure1_2yr_enrollment.png
│   ├── figure2_ny_vt_aid.png
│   ├── figure3_state_aid_map.png
│   ├── figure4_simulated_aid_map.png
│   ├── figure5_policy_simulation.png
│   └── figure6_winners_losers_map.png
│
├── .env                     # Local IPEDS URL configuration (not versioned)
├── requirements.txt
└── README.md
```

Raw and processed data are excluded from version control and can be regenerated locally using the scripts in this repository.

---

## Reproducing the Analysis

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure the environment

Create a `.env` file in the repository root containing the download URL templates:

```dotenv
NCES_HD_URL_TEMPLATE=https://nces.ed.gov/ipeds/datacenter/data/HD{}.zip
NCES_SFA_URL_TEMPLATE=https://nces.ed.gov/ipeds/datacenter/data/SFA{}.zip
```

Relative directory paths are resolved against the repository root by default. To use a different base directory, optionally set `BASE_PROJECT_PATH` in `.env`. Absolute paths and paths beginning with `~` are also supported.

### 3. Run the complete workflow

```bash
python script/main.py
```

This downloads and extracts the data, exports the clean panel, and generates the figures using these defaults. No keyboard input is required.

| Argument | Default | Purpose |
| --- | --- | --- |
| `--start-year` | `2010` | First academic year, coded by starting year |
| `--end-year` | `2015` | Last academic year, inclusive |
| `--download-dir` | `data/raw` | Downloaded ZIP files |
| `--extract-dir` | `data/interim` | Extracted annual CSV files |
| `--clean-dir` | `data/cleaned` | Cleaned CSV and Parquet panel |
| `--output-dir` | `figure` | Generated figures |

Override only the values you want to change:

```bash
python script/main.py \
    --download-dir data/downloads \
    --extract-dir data/extracted \
    --clean-dir data/custom_clean \
    --output-dir figure/custom
```

The analysis compares 2010 with 2015 and uses 2015 for aid and policy calculations, so the complete workflow requires a year range containing both 2010 and 2015. The download and cleaning scripts can also process other year ranges.

### 4. Run individual stages

```bash
python script/data_download.py
python script/data_clean.py
python script/plot.py
```

Each stage uses the same relevant defaults:

* `data_download.py` accepts `--start-year`, `--end-year`, `--download-dir`, and `--extract-dir`.
* `data_clean.py` accepts `--start-year`, `--end-year`, `--extract-dir`, and `--clean-dir`.
* `plot.py` accepts `--clean-dir` and `--output-dir`, and reads `cleaned_panel.parquet` from the clean directory.

When running stages separately with custom directories, pass the same extract directory to download and cleaning, and the same clean directory to cleaning and plotting. For example:

```bash
python script/data_download.py --extract-dir data/extracted
python script/data_clean.py --extract-dir data/extracted --clean-dir data/custom_clean
python script/plot.py --clean-dir data/custom_clean --output-dir figure/custom
```

Use `--help` with any script to see its options:

```bash
python script/main.py --help
```

---

## Tools

**Python · pandas · NumPy · Requests · concurrent.futures · Matplotlib · Seaborn · Plotly · Parquet**

The project demonstrates an end-to-end empirical research workflow: **data acquisition → panel construction → sample selection → descriptive analysis → policy simulation → visualization → policy communication**.
