from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_DATASET_NAME = "financial_expenses_dataset_raw.csv"
CLEANED_DATASET_NAME = "financial_expenses_dataset_cleaned.csv"

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
CLEANED_DATA_DIR = PROJECT_ROOT / "data" / "cleaned"
OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"

RAW_DATA_PATH = RAW_DATA_DIR / BASE_DATASET_NAME
CLEANED_DATA_PATH = CLEANED_DATA_DIR / CLEANED_DATASET_NAME

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
