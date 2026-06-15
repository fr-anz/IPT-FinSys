from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_DATASET_NAME = "financial_expenses_dataset_raw.csv"
CLEANED_DATASET_NAME = "financial_expenses_dataset_cleaned.csv"

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
CLEANED_DATA_DIR = PROJECT_ROOT / "data" / "cleaned"
OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"

RAW_DATA_PATH = RAW_DATA_DIR / BASE_DATASET_NAME
CLEANED_DATA_PATH = CLEANED_DATA_DIR / CLEANED_DATASET_NAME

CATEGORY_SUMMARY_NAME = "financial_expenses_dataset_category_summary.csv"
MONTHLY_SUMMARY_NAME = "financial_expenses_dataset_monthly_summary.csv"
PAYMENT_SUMMARY_NAME = "financial_expenses_dataset_payment_summary.csv"
BUDGET_SUMMARY_NAME = "financial_expenses_dataset_budget_summary.csv"

CATEGORY_SUMMARY_PATH = OUTPUTS_DIR / CATEGORY_SUMMARY_NAME
MONTHLY_SUMMARY_PATH = OUTPUTS_DIR / MONTHLY_SUMMARY_NAME
PAYMENT_SUMMARY_PATH = OUTPUTS_DIR / PAYMENT_SUMMARY_NAME
BUDGET_SUMMARY_PATH = OUTPUTS_DIR / BUDGET_SUMMARY_NAME

EXPECTED_COLUMNS = [
    "transaction_id",
    "date",
    "month",
    "account_type",
    "category",
    "subcategory",
    "merchant",
    "amount_php",
    "payment_method",
    "necessity_type",
    "status",
    "budget_limit_php",
    "notes",
]
