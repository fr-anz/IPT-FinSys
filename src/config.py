from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_DATASET_NAME = "family_finance_dataset_raw.csv"
CLEANED_DATASET_NAME = "family_finance_dataset_cleaned.csv"

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
    "household_id",
    "region",
    "province_city",
    "family_size",
    "dependent_count",
    "monthly_net_income_php",
    "income_class_assumption",
    "housing_status",
    "transport_profile",
    "schooling_profile",
    "transaction_type",
    "cash_flow_direction",
    "category",
    "subcategory",
    "merchant",
    "description",
    "amount_php",
    "payment_method",
    "channel",
    "necessity_type",
    "is_recurring",
    "budget_category",
    "budget_limit_php",
    "budget_period",
    "member_role",
    "school_related",
    "health_related",
    "debt_related",
    "savings_related",
    "status",
    "receipt_available",
    "notes",
    "outlier_flag",
    "outlier_reason",
]
