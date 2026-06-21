# Dataset Dictionary

Dataset: `family_finance_dataset_raw.csv`

This document describes the dataset used by the Financial Expense Monitoring
Dashboard. The raw dataset is stored in `data/raw/family_finance_dataset_raw.csv`
and the cleaned output is written to
`data/cleaned/family_finance_dataset_cleaned.csv` by `src/data_cleaning.py`.

The dataset is a **simulated Filipino family finance ledger** built for the
INTE 202 final project. It models one household's transactions (income,
expenses, savings, and debt payments) across roughly two years so the project
can demonstrate cleaning, analysis, statistics, and visualization.

## Source

- **Origin:** Instructor-provided / project-generated synthetic dataset created
  for academic simulation (no real personal financial data).
- **Format:** Single CSV file, comma-separated, UTF-8, one row per transaction.
- **Scope:** One simulated household (`HH-PH-0001`) in Region III - Central
  Luzon (Bulacan / NCR commuter area).

## Size and structure

| Property | Raw dataset | Cleaned dataset |
| --- | --- | --- |
| Records (rows) | 1,012 | 965 |
| Columns | 35 | 37 |
| Rows removed by cleaning | — | 47 (invalid dates, missing amounts, exact duplicates) |
| Added columns | — | `outlier_flag`, `outlier_reason` |

Cleaning renames four source columns: `transaction_date` -> `date`,
`merchant_or_source` -> `merchant`, `necessity_level` -> `necessity_type`, and
`monthly_budget_php` -> `budget_limit_php`. All other columns keep their names.

## Data types (after cleaning)

| Type | Columns |
| --- | --- |
| Date / period (text) | `date` (YYYY-MM-DD), `month` (YYYY-MM) |
| Integer | `family_size`, `dependent_count` |
| Float (PHP) | `monthly_net_income_php`, `amount_php`, `budget_limit_php` |
| Categorical / text | all remaining identifier, label, and note columns |
| Boolean-style (`Yes` / `No` / `Unknown`) | `is_recurring`, `school_related`, `health_related`, `debt_related`, `savings_related`, `receipt_available` |

## Column definitions

Column names below use the **cleaned** dataset. The raw source name is given in
parentheses when cleaning renames it.

| Column | Type | Description | Cleaning / usage notes |
| --- | --- | --- | --- |
| `transaction_id` | Text | Unique transaction reference such as `FEM-PH-202505-0669`. | Missing IDs filled with `Unknown`; used with date, category, amount, and description to drop exact duplicates. |
| `date` (`transaction_date`) | Date | Exact transaction date. | Parsed from several formats to `YYYY-MM-DD`; rows with missing or unparseable dates are removed. |
| `month` | Year-month | Reporting month such as `2025-05`. | Rebuilt from `date` so monthly trend analysis stays consistent. |
| `household_id` | Text | Household identifier. | Single household (`HH-PH-0001`) in this simulation. |
| `region` | Categorical | Philippine region of the household. | Standardized text. |
| `province_city` | Categorical | Province / city locale. | Raw has inconsistent variants (e.g. `Bulacan / NCR commuter area` vs `Bulacan-NCR`) standardized to title case. |
| `family_size` | Integer | Number of household members. | Converted to numeric. |
| `dependent_count` | Integer | Number of dependents. | Converted to numeric. |
| `monthly_net_income_php` | Float (PHP) | Household monthly net income. | Converted to numeric; used for savings-rate and debt-ratio context. |
| `income_class_assumption` | Categorical | Income-bracket assumption used for the simulation. | Standardized text. |
| `housing_status` | Categorical | Housing situation such as `Renting`. | Standardized text. |
| `transport_profile` | Categorical | Commute / transport profile. | Standardized text. |
| `schooling_profile` | Categorical | Schooling context for dependents. | Standardized text. |
| `transaction_type` | Categorical | One of `Income`, `Expense`, `Savings`, `Debt Payment`. | Raw has casing/whitespace noise (`expense`, `EXPENSE`, ` Expense`); normalized, and inferred from category/cash flow when missing. |
| `cash_flow_direction` | Categorical | `Inflow` or `Outflow`. | Standardized text. |
| `category` | Categorical | Main spending group (13 values, e.g. `Food`, `Utilities`, `Connectivity`, `Lifestyle & Misc`). | Mapped to consistent names (e.g. `Groceries` -> `Food`, `Transport` -> `Transportation`); missing values inferred from budget category / transaction type or set to `Unknown`. Drives category totals, charts, and insights. |
| `subcategory` | Categorical | Finer label under the category (e.g. `Internet`, `Streaming`). | Missing values filled with `Unknown`; used in frequency distributions. |
| `merchant` (`merchant_or_source`) | Text | Store, vendor, platform, or income source. | Missing values filled with `Unknown`; used in frequency distributions. |
| `description` | Text | Short description of the transaction. | Missing values filled with `Unknown`. |
| `amount_php` | Float (PHP) | Transaction amount. `transaction_type` indicates income / expense / savings / debt; negative values represent refunds. | Stripped of currency symbols/commas and converted to numeric; rows with invalid amounts removed. Core field for statistics, totals, trends, charts, and insights. |
| `payment_method` | Categorical | Channel used (`Cash`, `GCash`, `Maya`, `Bank Transfer`, `Credit Card`). | Standardized names; missing values filled with `Unknown`. Used for filters and frequency distributions. |
| `channel` | Categorical | Where the transaction happened (`Physical Store`, `Bill Payment`, `School`, ...). | Standardized text. |
| `necessity_type` (`necessity_level`) | Categorical | Priority class: `Need`, `Want`, `Obligation`, `Savings`, `Emergency`. | Raw has casing/whitespace noise (`need`, `NEED`, ` Need`); normalized. Used for filters, the needs/wants split, and insights. |
| `is_recurring` | Boolean-style | Whether the transaction recurs. | Normalized to `Yes` / `No` / `Unknown`. |
| `budget_category` | Categorical | Budget grouping the transaction maps to. | Standardized like `category`. |
| `budget_limit_php` (`monthly_budget_php`) | Float (PHP) | Budget limit for the category / period. | Converted to numeric; missing values filled with `0.0`. Used for budget summaries and correlation with `amount_php`. |
| `budget_period` | Categorical | `Monthly`, `Weekly`, or `Irregular`. | Standardized text. |
| `member_role` | Categorical | Household member responsible (`Household`, `Father`, `Mother`, ...). | Standardized text. |
| `school_related` | Boolean-style | Flags school-related spending. | Normalized to `Yes` / `No` / `Unknown`. |
| `health_related` | Boolean-style | Flags health-related spending. | Normalized to `Yes` / `No` / `Unknown`. |
| `debt_related` | Boolean-style | Flags debt-related transactions. | Normalized to `Yes` / `No` / `Unknown`. |
| `savings_related` | Boolean-style | Flags savings-related transactions. | Normalized to `Yes` / `No` / `Unknown`. |
| `status` | Categorical | Transaction state (`Paid`, `Received`, `Unknown`). | Raw has casing/whitespace noise (`paid`, `PAID`, ` Paid`); normalized. |
| `receipt_available` | Boolean-style | Whether a receipt exists. | Normalized to `Yes` / `No` / `Unknown`. |
| `notes` | Text | Short free-text note. | ~49% missing in raw; filled with `No notes provided`. Excluded from frequency distributions because it is descriptive. |
| `outlier_flag` | Categorical | `Yes` / `No` flag added during cleaning. | Set by `_detect_outliers`: negative amounts, very high amounts (>= PHP 10,000 non-income), or values above the per-category IQR range. |
| `outlier_reason` | Text | Reason an outlier was flagged. | One or more of `Negative amount`, `Very high amount`, `Above category range`; `None` when not an outlier. |

## Known issues in the raw dataset

The raw dataset intentionally contains quality problems so the project can
demonstrate cleaning:

- **Exact duplicate rows:** 9 fully duplicated records.
- **Missing values:** 615 blank cells across 16 columns. The largest gaps are
  `notes` (494), `subcategory` (16), `transaction_id` (14), `amount_php` (14),
  and `monthly_budget_php` (12).
- **Inconsistent capitalization and whitespace:** label columns such as
  `transaction_type` (`expense`, `EXPENSE`, ` Expense`), `necessity_level`
  (`need`, `NEED`, ` Need`), and `status` (`paid`, `PAID`, ` Paid`).
- **Inconsistent locale spellings:** `province_city` has several variants of the
  same place.
- **Invalid records:** rows with unparseable dates or missing amounts cannot be
  analyzed and are removed.
- **Outliers:** negative refunds, unusually large amounts, and category-level
  extremes that are flagged rather than dropped.

## How the dashboard uses these columns

- **Summary statistics:** `amount_php` (mean, median, mode, min, max, std).
- **Category totals and rankings:** `category`, `amount_php`.
- **Monthly trends:** `date`, `month`, `amount_php`.
- **Budget analysis:** `budget_limit_php`, `amount_php`, `category`.
- **Correlation analysis:** numeric fields (`amount_php`, `family_size`,
  `dependent_count`, `monthly_net_income_php`).
- **Frequency distributions:** categorical fields such as `category`,
  `payment_method`, `status`, and `necessity_type`.
- **Visualizations:** category bar chart, monthly line chart, category pie
  chart, and amount histogram.
