from datetime import datetime
import re

import pandas as pd

from src.config import CLEANED_DATA_PATH, RAW_DATA_PATH


ALLOWED_TRANSACTION_TYPES = {"Income", "Expense", "Savings", "Debt Payment"}
BOOLEAN_COLUMNS = [
    "is_recurring",
    "school_related",
    "health_related",
    "debt_related",
    "savings_related",
    "receipt_available",
]
ID_COLUMNS = ["transaction_id", "household_id"]
TEXT_COLUMNS = [
    "income_class_assumption",
    "housing_status",
    "transport_profile",
    "schooling_profile",
    "cash_flow_direction",
    "category",
    "subcategory",
    "merchant",
    "description",
    "payment_method",
    "channel",
    "necessity_type",
    "budget_category",
    "budget_period",
    "member_role",
    "status",
    "notes",
]
NUMERIC_COLUMNS = [
    "family_size",
    "dependent_count",
    "monthly_net_income_php",
    "amount_php",
    "budget_limit_php",
]
DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
]


def _to_snake_case(column_name):
    """Convert a source column name to lowercase snake_case."""
    clean_name = str(column_name).strip().replace("\ufeff", "")
    clean_name = re.sub(r"[^0-9A-Za-z]+", "_", clean_name)
    return clean_name.strip("_").lower()


def _standardize_columns(df):
    cleaned_df = df.copy()
    cleaned_df.columns = [_to_snake_case(column) for column in cleaned_df.columns]
    return cleaned_df.rename(
        columns={
            "transaction_date": "date",
            "merchant_or_source": "merchant",
            "necessity_level": "necessity_type",
            "monthly_budget_php": "budget_limit_php",
        }
    )


def _clean_numeric(series):
    return pd.to_numeric(
        series.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.replace("₱", "", regex=False)
        .str.replace("PHP", "", case=False, regex=False)
        .str.replace(",", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


def _parse_date_value(value, expected_month=None):
    if pd.isna(value):
        return pd.NaT

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return pd.NaT

    candidates = []
    for date_format in DATE_FORMATS:
        try:
            candidates.append(pd.Timestamp(datetime.strptime(text, date_format)))
        except ValueError:
            continue

    if not candidates:
        return pd.NaT

    month_text = None
    if expected_month is not None and not pd.isna(expected_month):
        month_text = str(expected_month).strip()[:7]

    if month_text:
        for candidate in candidates:
            if candidate.strftime("%Y-%m") == month_text:
                return candidate

    return candidates[0]


def _parse_dates(df):
    if "date" not in df.columns:
        return df

    cleaned_df = df.copy()
    expected_months = cleaned_df["month"] if "month" in cleaned_df.columns else None
    if expected_months is None:
        cleaned_df["date"] = cleaned_df["date"].apply(_parse_date_value)
    else:
        cleaned_df["date"] = [
            _parse_date_value(value, expected_month)
            for value, expected_month in zip(cleaned_df["date"], expected_months)
        ]
    return cleaned_df


def _is_missing(series):
    return series.isna() | series.astype(str).str.strip().str.lower().isin(
        {"", "nan", "none", "null"}
    )


def _title_text(value):
    if pd.isna(value):
        return pd.NA

    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return pd.NA

    normalized = re.sub(r"\s+", " ", text).title()
    replacements = {
        "Gcash": "GCash",
        "Maya": "Maya",
        "Php": "PHP",
        "Ncr": "NCR",
        "Uv": "UV",
        "Pta": "PTA",
        "Bdo": "BDO",
        "Atm": "ATM",
        "Debt/Loans": "Debt/Loans",
        "Bank/App": "Bank/App",
        "Lifestyle & Misc": "Lifestyle & Misc",
    }
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized


def _standardize_text_column(series):
    return series.apply(_title_text)


def _normalize_boolean(value):
    if pd.isna(value):
        return "Unknown"

    text = str(value).strip().lower()
    if text in {"yes", "y", "true", "1"}:
        return "Yes"
    if text in {"no", "n", "false", "0"}:
        return "No"
    return "Unknown"


def _normalize_transaction_type(row):
    transaction_type = _title_text(row.get("transaction_type"))
    if transaction_type in ALLOWED_TRANSACTION_TYPES:
        return transaction_type

    category = str(row.get("category", "")).strip().lower()
    cash_flow_direction = str(row.get("cash_flow_direction", "")).strip().lower()
    debt_related = str(row.get("debt_related", "")).strip().lower()
    savings_related = str(row.get("savings_related", "")).strip().lower()

    if category == "income" or cash_flow_direction == "inflow":
        return "Income"
    if category in {"savings", "emergency fund"} or savings_related == "yes":
        return "Savings"
    if category == "debt/loans" or debt_related == "yes":
        return "Debt Payment"
    return "Expense"


def _standardize_category(value):
    category = _title_text(value)
    if pd.isna(category):
        return pd.NA

    category_map = {
        "Educ": "Education",
        "Grocery": "Food",
        "Groceries": "Food",
        "Transport": "Transportation",
        "Debt Loans": "Debt/Loans",
        "Debt/Loan": "Debt/Loans",
        "Debt/Loans": "Debt/Loans",
        "Lifestyle And Misc": "Lifestyle & Misc",
    }
    return category_map.get(category, category)


def _fill_obvious_category(row):
    category = row.get("category")
    if not pd.isna(category):
        return category

    budget_category = row.get("budget_category")
    if not pd.isna(budget_category):
        return budget_category

    transaction_type = row.get("transaction_type")
    if transaction_type in {"Income", "Savings"}:
        return transaction_type
    if transaction_type == "Debt Payment":
        return "Debt/Loans"
    return "Unknown"


def _detect_outliers(df):
    outlier_flag = pd.Series("No", index=df.index)
    outlier_reason = pd.Series("", index=df.index, dtype="object")

    negative_amounts = df["amount_php"] < 0
    outlier_flag.loc[negative_amounts] = "Yes"
    outlier_reason.loc[negative_amounts] = "Negative amount"

    high_amounts = (df["amount_php"] >= 10000) & (df["transaction_type"] != "Income")
    outlier_flag.loc[high_amounts] = "Yes"
    outlier_reason.loc[high_amounts] = outlier_reason.loc[high_amounts].apply(
        lambda reason: "; ".join(filter(None, [reason, "Very high amount"]))
    )

    grouped = df.groupby("category", observed=True)["amount_php"]
    q1 = grouped.transform(lambda values: values.quantile(0.25))
    q3 = grouped.transform(lambda values: values.quantile(0.75))
    iqr = q3 - q1
    category_outliers = df["amount_php"] > (q3 + (1.5 * iqr))
    category_outliers = category_outliers & iqr.notna() & (iqr > 0)
    outlier_flag.loc[category_outliers] = "Yes"
    outlier_reason.loc[category_outliers] = outlier_reason.loc[
        category_outliers
    ].apply(lambda reason: "; ".join(filter(None, [reason, "Above category range"])))

    return outlier_flag, outlier_reason.replace("", "None")


def clean_dataset(df):
    """Clean and export the family finance dataset used by the dashboard."""
    cleaned_df = _standardize_columns(df)

    cleaned_df = _parse_dates(cleaned_df)

    for column in NUMERIC_COLUMNS:
        if column in cleaned_df.columns:
            cleaned_df[column] = _clean_numeric(cleaned_df[column])

    for column in ID_COLUMNS:
        if column in cleaned_df.columns:
            cleaned_df[column] = cleaned_df[column].where(
                ~_is_missing(cleaned_df[column]), "Unknown"
            )
            cleaned_df[column] = cleaned_df[column].astype(str).str.strip()

    for column in TEXT_COLUMNS:
        if column in cleaned_df.columns:
            cleaned_df[column] = _standardize_text_column(cleaned_df[column])

    for column in BOOLEAN_COLUMNS:
        if column in cleaned_df.columns:
            cleaned_df[column] = cleaned_df[column].apply(_normalize_boolean)

    if "category" in cleaned_df.columns:
        cleaned_df["category"] = cleaned_df["category"].apply(_standardize_category)

    if "budget_category" in cleaned_df.columns:
        cleaned_df["budget_category"] = cleaned_df["budget_category"].apply(
            _standardize_category
        )

    if "transaction_type" in cleaned_df.columns:
        cleaned_df["transaction_type"] = cleaned_df.apply(
            _normalize_transaction_type, axis=1
        )

    if {"category", "budget_category", "transaction_type"}.issubset(cleaned_df.columns):
        cleaned_df["category"] = cleaned_df.apply(_fill_obvious_category, axis=1)
    elif "category" in cleaned_df.columns:
        cleaned_df["category"] = cleaned_df["category"].fillna("Unknown")

    if "payment_method" in cleaned_df.columns:
        cleaned_df["payment_method"] = cleaned_df["payment_method"].fillna("Unknown")

    for column in [
        "subcategory",
        "merchant",
        "description",
        "channel",
        "necessity_type",
    ]:
        if column in cleaned_df.columns:
            cleaned_df[column] = cleaned_df[column].fillna("Unknown")

    if "status" in cleaned_df.columns:
        cleaned_df["status"] = cleaned_df["status"].fillna("Unknown")

    if "notes" in cleaned_df.columns:
        cleaned_df["notes"] = cleaned_df["notes"].fillna("No notes provided")

    if "date" in cleaned_df.columns:
        cleaned_df = cleaned_df.dropna(subset=["date"])
        cleaned_df["date"] = cleaned_df["date"].dt.strftime("%Y-%m-%d")
        cleaned_df["month"] = (
            pd.to_datetime(cleaned_df["date"]).dt.to_period("M").astype(str)
        )

    if "amount_php" in cleaned_df.columns:
        cleaned_df = cleaned_df.dropna(subset=["amount_php"])

    duplicate_subset = [
        column
        for column in ["transaction_id", "date", "category", "amount_php", "description"]
        if column in cleaned_df.columns
    ]
    if duplicate_subset:
        cleaned_df = cleaned_df.drop_duplicates(subset=duplicate_subset, keep="first")

    if {"amount_php", "category", "transaction_type"}.issubset(cleaned_df.columns):
        cleaned_df["outlier_flag"], cleaned_df["outlier_reason"] = _detect_outliers(
            cleaned_df
        )

    categorical_columns = [
        "transaction_type",
        "cash_flow_direction",
        "category",
        "subcategory",
        "payment_method",
        "channel",
        "necessity_type",
        "budget_category",
        "budget_period",
        "member_role",
        "status",
        "outlier_flag",
        "outlier_reason",
    ]
    for column in categorical_columns:
        if column in cleaned_df.columns:
            cleaned_df[column] = cleaned_df[column].astype("category")

    CLEANED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    cleaned_df.to_csv(CLEANED_DATA_PATH, index=False)

    return cleaned_df


if __name__ == "__main__":
    raw_df = pd.read_csv(RAW_DATA_PATH)
    cleaned_df = clean_dataset(raw_df)

    print(cleaned_df.head())
    print(cleaned_df.shape)
