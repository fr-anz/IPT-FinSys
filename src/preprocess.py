import numpy as np
import pandas as pd

from src.config import (
    CLEANED_DATA_PATH,
    MONTHLY_AGGREGATION_PATH,
    PREPROCESSING_OUTPUTS_DIR,
    PROCESSED_TRANSACTIONS_PATH,
)


ALLOWED_TRANSACTION_TYPES = {"Income", "Expense", "Savings", "Debt Payment"}
SAVINGS_RATE_TARGET = 20.0
DEBT_RATIO_LIMIT = 30.0
EMERGENCY_FUND_TARGET = 10.0

NEEDS_LABELS = {
    "groceries",
    "rent",
    "utilities",
    "transportation",
    "education",
    "healthcare",
    "food",
    "housing",
    "connectivity",
    "drinking water",
    "electricity",
    "internet",
    "lpg",
    "school allowance",
    "school project",
    "school supplies",
    "pta/school fee",
    "water bill",
}
WANTS_LABELS = {
    "entertainment",
    "dining out",
    "shopping",
    "leisure",
    "lifestyle & misc",
    "fast food",
    "streaming",
    "gifts",
}
SAVINGS_LABELS = {"savings", "emergency fund", "investments"}
DEBT_LABELS = {"loan payment", "credit card payment", "debt/loans", "debt loans"}


def _require_columns(df, required_columns):
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise KeyError(
            "Missing required preprocessing columns: " + ", ".join(missing_columns)
        )


def _date_column(df):
    if "transaction_date" in df.columns:
        return "transaction_date"
    if "date" in df.columns:
        return "date"
    raise KeyError("Missing required preprocessing columns: transaction_date or date")


def _amount_column(df):
    if "actual_amount" in df.columns:
        return "actual_amount"
    if "amount_php" in df.columns:
        return "amount_php"
    raise KeyError("Missing required preprocessing columns: actual_amount or amount_php")


def _budget_column(df):
    if "budget_amount" in df.columns:
        return "budget_amount"
    if "budget_limit_php" in df.columns:
        return "budget_limit_php"
    raise KeyError(
        "Missing required preprocessing columns: budget_amount or budget_limit_php"
    )


def _safe_percent(numerator, denominator):
    return np.where(denominator > 0, (numerator / denominator) * 100, 0.0)


def _safe_ratio(numerator, denominator):
    return np.where(denominator > 0, numerator / denominator, 0.0)


def _score_against_target(values, target):
    return np.minimum(_safe_percent(values, target), 100.0)


def _inverse_score_against_limit(values, limit):
    return np.maximum(100.0 - np.minimum(_safe_percent(values, limit), 100.0), 0.0)


def _normalize_label(value):
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def _classify_expense_group(row):
    labels = [
        _normalize_label(row.get("category")),
        _normalize_label(row.get("subcategory")),
        _normalize_label(row.get("budget_category")),
        _normalize_label(row.get("description")),
    ]

    if any(label in SAVINGS_LABELS for label in labels):
        return "Savings"
    if any(label in DEBT_LABELS for label in labels):
        return "Debt"
    if any(label in WANTS_LABELS for label in labels):
        return "Wants"
    if any(label in NEEDS_LABELS for label in labels):
        return "Needs"
    return "Unknown"


def _add_date_features(df, date_column):
    processed_df = df.copy()
    parsed_dates = pd.to_datetime(processed_df[date_column], errors="coerce")
    if parsed_dates.isna().any():
        raise ValueError("Preprocessing requires valid transaction dates.")

    processed_df[date_column] = parsed_dates.dt.strftime("%Y-%m-%d")
    processed_df["year"] = parsed_dates.dt.year
    processed_df["month_number"] = parsed_dates.dt.month
    processed_df["month_name"] = parsed_dates.dt.month_name()
    processed_df["year_month"] = parsed_dates.dt.to_period("M").astype(str)
    processed_df["quarter"] = "Q" + parsed_dates.dt.quarter.astype(str)
    return processed_df


def _add_transaction_features(df, amount_column, budget_column):
    processed_df = df.copy()
    processed_df["actual_amount"] = pd.to_numeric(
        processed_df[amount_column], errors="coerce"
    )
    processed_df["budget_amount"] = pd.to_numeric(
        processed_df[budget_column], errors="coerce"
    ).fillna(0.0)

    if processed_df["actual_amount"].isna().any():
        raise ValueError("Preprocessing requires valid transaction amounts.")

    processed_df["budget_variance"] = (
        processed_df["actual_amount"] - processed_df["budget_amount"]
    )
    processed_df["expense_group"] = processed_df.apply(
        _classify_expense_group, axis=1
    )
    return processed_df


def _monthly_type_totals(df):
    metric_df = df.copy()
    metric_df["metric_amount"] = metric_df["actual_amount"].clip(lower=0)
    metric_df["transaction_type"] = metric_df["transaction_type"].where(
        metric_df["transaction_type"].isin(ALLOWED_TRANSACTION_TYPES), "Expense"
    )

    monthly = pd.DataFrame({"year_month": sorted(metric_df["year_month"].unique())})
    type_map = {
        "Income": "total_income",
        "Expense": "total_expenses",
        "Savings": "total_savings",
        "Debt Payment": "total_debt_payments",
    }

    for transaction_type, output_column in type_map.items():
        totals = (
            metric_df[metric_df["transaction_type"] == transaction_type]
            .groupby("year_month")["metric_amount"]
            .sum()
        )
        monthly[output_column] = monthly["year_month"].map(totals).fillna(0.0)

    return monthly, metric_df


def _budget_adherence_by_month(metric_df):
    expense_df = metric_df[
        (metric_df["transaction_type"] == "Expense")
        & (metric_df["budget_amount"] > 0)
    ]
    if expense_df.empty:
        return pd.Series(dtype="float64")

    category_budget = (
        expense_df.groupby(["year_month", "category"], observed=True)
        .agg(
            actual_spend=("metric_amount", "sum"),
            budget_amount=("budget_amount", "max"),
        )
        .reset_index()
    )
    category_budget["within_budget"] = (
        category_budget["actual_spend"] <= category_budget["budget_amount"]
    )
    return category_budget.groupby("year_month")["within_budget"].mean() * 100


def _build_monthly_aggregation(processed_df):
    monthly, metric_df = _monthly_type_totals(processed_df)

    needs_expenses = (
        metric_df[
            (metric_df["expense_group"] == "Needs")
            & (metric_df["transaction_type"] == "Expense")
        ]
        .groupby("year_month")["metric_amount"]
        .sum()
    )
    emergency_fund = (
        metric_df[
            (metric_df["expense_group"] == "Savings")
            & (
                metric_df["category"].astype(str).str.lower().eq("emergency fund")
                | metric_df["subcategory"].astype(str).str.lower().eq("emergency fund")
                | metric_df["budget_category"]
                .astype(str)
                .str.lower()
                .eq("emergency fund")
            )
        ]
        .groupby("year_month")["metric_amount"]
        .sum()
    )
    monthly["needs_expenses"] = monthly["year_month"].map(needs_expenses).fillna(0.0)
    monthly["emergency_fund_contribution"] = (
        monthly["year_month"].map(emergency_fund).fillna(0.0)
    )

    monthly["income_expense_ratio"] = _safe_ratio(
        monthly["total_expenses"], monthly["total_income"]
    )
    monthly["savings_rate"] = _safe_percent(
        monthly["total_savings"], monthly["total_income"]
    )
    monthly["necessity_ratio"] = _safe_percent(
        monthly["needs_expenses"], monthly["total_expenses"]
    )
    monthly["debt_ratio"] = _safe_percent(
        monthly["total_debt_payments"], monthly["total_income"]
    )
    monthly["emergency_fund_rate"] = _safe_percent(
        monthly["emergency_fund_contribution"], monthly["total_income"]
    )

    budget_adherence = _budget_adherence_by_month(metric_df)
    monthly["budget_adherence_score"] = (
        monthly["year_month"].map(budget_adherence).fillna(0.0)
    )

    budget_component = monthly["budget_adherence_score"].clip(0, 100)
    savings_component = _score_against_target(
        monthly["savings_rate"], SAVINGS_RATE_TARGET
    )
    debt_component = _inverse_score_against_limit(
        monthly["debt_ratio"], DEBT_RATIO_LIMIT
    )
    emergency_component = _score_against_target(
        monthly["emergency_fund_rate"], EMERGENCY_FUND_TARGET
    )

    monthly["financial_health_score"] = (
        (budget_component * 0.40)
        + (savings_component * 0.30)
        + (debt_component * 0.20)
        + (emergency_component * 0.10)
    ).round(2)

    output_columns = [
        "year_month",
        "total_income",
        "total_expenses",
        "total_savings",
        "total_debt_payments",
        "income_expense_ratio",
        "savings_rate",
        "necessity_ratio",
        "budget_adherence_score",
        "financial_health_score",
    ]
    monthly[output_columns[1:]] = monthly[output_columns[1:]].round(2)
    return monthly[output_columns].sort_values("year_month").reset_index(drop=True)


def preprocess_dataset(df):
    """Return transaction-level features and monthly financial metrics."""
    _require_columns(df, ["transaction_type", "category"])
    date_column = _date_column(df)
    amount_column = _amount_column(df)
    budget_column = _budget_column(df)

    processed_df = _add_date_features(df, date_column)
    processed_df = _add_transaction_features(processed_df, amount_column, budget_column)
    monthly_aggregation = _build_monthly_aggregation(processed_df)

    return processed_df, monthly_aggregation


def load_and_preprocess_cleaned_dataset(path=CLEANED_DATA_PATH):
    """Load the cleaned project dataset and return both preprocessed dataframes."""
    cleaned_df = pd.read_csv(path)
    return preprocess_dataset(cleaned_df)


def save_preprocessed_outputs(
    processed_df,
    monthly_aggregation,
    processed_path=PROCESSED_TRANSACTIONS_PATH,
    monthly_path=MONTHLY_AGGREGATION_PATH,
):
    """Write preprocessing outputs to data/outputs/preprocessing and return paths."""
    PREPROCESSING_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    processed_df.to_csv(processed_path, index=False)
    monthly_aggregation.to_csv(monthly_path, index=False)
    return {
        "transactions": processed_path,
        "monthly_aggregation": monthly_path,
    }


def load_preprocess_and_save_cleaned_dataset(path=CLEANED_DATA_PATH):
    """Load the cleaned dataset, preprocess it, and save both output CSVs."""
    processed_df, monthly_aggregation = load_and_preprocess_cleaned_dataset(path)
    output_paths = save_preprocessed_outputs(processed_df, monthly_aggregation)
    return processed_df, monthly_aggregation, output_paths


if __name__ == "__main__":
    transactions, monthly_metrics, paths = load_preprocess_and_save_cleaned_dataset()
    print(transactions.head())
    print(monthly_metrics.head())
    print("Saved outputs:")
    for name, path in paths.items():
        print(f"{name}: {path}")
