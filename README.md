# Financial Expense Monitoring Dashboard

A minimal Python Streamlit starter dashboard for an INTE 202 final project. The app loads a financial expenses CSV file, shows a raw data preview, runs basic starter cleaning, displays a small summary, creates one sample chart, and shows placeholder insights.

This is only a minimal starter boilerplate. Each developer should expand only their assigned module.

## Setup

Install the required packages:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

## Dataset

Main dataset:

```text
financial_expenses_dataset_raw.csv
```

Expected raw dataset location:

```text
data/raw/financial_expenses_dataset_raw.csv
```

Expected cleaned dataset location:

```text
data/cleaned/financial_expenses_dataset_cleaned.csv
```

## Starter Structure

```text
app.py
requirements.txt
README.md
data/
  raw/
  cleaned/
  outputs/
src/
  __init__.py
  config.py
  data_loader.py
  data_cleaning.py
  analysis.py
  visualizations.py
  insights.py
docs/
  developer_tasks.md
  project_notes.md
```
