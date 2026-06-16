from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_DATASET_NAME = "family_finance_dataset_raw.csv"
CLEANED_DATASET_NAME = "family_finance_dataset_cleaned.csv"

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
CLEANED_DATA_DIR = PROJECT_ROOT / "data" / "cleaned"
OUTPUTS_DIR = PROJECT_ROOT / "data" / "outputs"
PREPROCESSING_OUTPUTS_DIR = OUTPUTS_DIR / "preprocessing"
PROCESSED_DATA_DIR = OUTPUTS_DIR / "processed"
ANALYSIS_OUTPUTS_DIR = PROCESSED_DATA_DIR / "analysis"

RAW_DATA_PATH = RAW_DATA_DIR / BASE_DATASET_NAME
CLEANED_DATA_PATH = CLEANED_DATA_DIR / CLEANED_DATASET_NAME

CATEGORY_SUMMARY_NAME = "category_summary.csv"
MONTHLY_SUMMARY_NAME = "monthly_summary.csv"
PAYMENT_SUMMARY_NAME = "payment_summary.csv"
BUDGET_SUMMARY_NAME = "budget_variance_summary.csv"
EXPENSE_GROUP_SUMMARY_NAME = "expense_group_summary.csv"
FINANCIAL_HEALTH_SUMMARY_NAME = "financial_health_summary.csv"
PROCESSED_TRANSACTIONS_NAME = "family_finance_transactions_processed.csv"
MONTHLY_AGGREGATION_NAME = "family_finance_monthly_aggregated.csv"

CATEGORY_SUMMARY_PATH = ANALYSIS_OUTPUTS_DIR / CATEGORY_SUMMARY_NAME
MONTHLY_SUMMARY_PATH = ANALYSIS_OUTPUTS_DIR / MONTHLY_SUMMARY_NAME
PAYMENT_SUMMARY_PATH = ANALYSIS_OUTPUTS_DIR / PAYMENT_SUMMARY_NAME
BUDGET_SUMMARY_PATH = ANALYSIS_OUTPUTS_DIR / BUDGET_SUMMARY_NAME
EXPENSE_GROUP_SUMMARY_PATH = ANALYSIS_OUTPUTS_DIR / EXPENSE_GROUP_SUMMARY_NAME
FINANCIAL_HEALTH_SUMMARY_PATH = (
    ANALYSIS_OUTPUTS_DIR / FINANCIAL_HEALTH_SUMMARY_NAME
)
PROCESSED_TRANSACTIONS_PATH = PREPROCESSING_OUTPUTS_DIR / PROCESSED_TRANSACTIONS_NAME
MONTHLY_AGGREGATION_PATH = PREPROCESSING_OUTPUTS_DIR / MONTHLY_AGGREGATION_NAME

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
