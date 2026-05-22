# ED_data

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