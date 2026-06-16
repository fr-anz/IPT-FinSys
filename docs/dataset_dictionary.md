# Dataset Dictionary

Dataset: `financial_expenses_dataset_raw.csv`

This file documents the columns used by the Financial Expense Monitoring Dashboard. The raw dataset is stored in `data/raw/`, and the cleaned output is written to `data/cleaned/`.

## Column Definitions

| Column | Type | Description | Cleaning / Usage Notes |
| --- | --- | --- | --- |
| `transaction_id` | Text | Unique transaction reference such as `FEM-0001`. | Used to identify duplicate transactions. Rows with missing IDs are removed, and duplicate IDs keep the first record. |
| `date` | Date | Exact transaction date. | Converted to a valid date value. Rows with missing or invalid dates are removed. |
| `month` | Year-month | Reporting month for the transaction, such as `2025-07`. | Rebuilt from `date` during cleaning to keep monthly trend analysis consistent. |
| `account_type` | Categorical text | Account context for the expense, such as `Personal`, `Student`, `Household`, or `Freelance`. | Missing values are filled with `Unknown` and stored as a category in the cleaned dataset. |
| `category` | Categorical text | Main expense group, such as `Food & Dining`, `Transportation`, `Shopping`, `Utilities`, `Savings`, or `Rent`. | Standardized to consistent category names. Unknown or unmapped values are assigned to `Others`. Used for category totals, charts, and insights. |
| `subcategory` | Categorical text | More specific expense label under the main category, such as `Fast Food`, `Gaming`, or `Mobile Load`. | Missing values are filled with `Unknown` and used in frequency distribution analysis. |
| `merchant` | Text | Store, vendor, platform, or service provider where the transaction occurred. | Missing values are filled with `Unknown`. Used for frequency distribution analysis. |
| `amount_php` | Numeric | Transaction amount in Philippine pesos. Positive values are expenses; negative values represent refunds. | Converted to numeric. Rows with invalid amount values are removed. Refunded records are stored as negative amounts. Used for statistical analysis, totals, trends, charts, and insights. |
| `payment_method` | Categorical text | Payment channel used, such as `GCash`, `Maya`, `Cash`, `Credit Card`, `Debit Card`, `Bank Transfer`, or `BDO Online`. | Standardized to consistent names. Unmapped values default to `Cash`. Used for filters and frequency distribution analysis. |
| `necessity_type` | Categorical text | Classifies the transaction as `Need`, `Want`, `Mixed`, or `Savings`. | Missing values are filled with `Unknown`. Used for filters, frequency distributions, and insight generation. |
| `status` | Categorical text | Transaction state, such as `Paid`, `Pending`, `Cancelled`, or `Refunded`. | Standardized to consistent names. Missing or unrecognized statuses default to `Paid`, except negative amounts can be marked as `Refunded`. Used for filters and cleaning logic. |
| `budget_limit_php` | Numeric | Budget limit in Philippine pesos associated with the transaction category or budget group. | Converted to numeric and missing values are filled with `0.0`. Used for budget summaries and correlation analysis with `amount_php`. |
| `notes` | Text | Short transaction note, such as `Budget concern`, `Recurring bill`, or `Regular expense`. | Missing values are filled with `No notes provided`. Excluded from frequency distributions because it is descriptive rather than analytical. |

## Dataset Quality Notes

The raw dataset intentionally includes duplicate records, inconsistent capitalization, missing values, invalid values, and noisy entries so the project can demonstrate data cleaning and preprocessing. The cleaning pipeline removes invalid key records, standardizes categories and payment/status values, converts dates and numeric fields, handles refunds, and exports the cleaned CSV.

## Analysis Use

The dashboard uses these columns for:

- Summary statistics: `amount_php`
- Category totals: `category`, `amount_php`
- Monthly trends: `date`, `month`, `amount_php`
- Budget analysis: `budget_limit_php`, `amount_php`, `category`
- Correlation analysis: numeric fields such as `amount_php` and `budget_limit_php`
- Frequency distributions: categorical fields such as `category`, `payment_method`, `status`, and `necessity_type`
- Visualizations: category bar chart, monthly line chart, category pie chart, amount histogram, and budget-vs-actual chart
