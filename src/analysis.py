import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from src.config import (
        ANALYSIS_OUTPUTS_DIR,
        BUDGET_SUMMARY_PATH,
        CATEGORY_SUMMARY_PATH,
        EXPENSE_GROUP_SUMMARY_PATH,
        FINANCIAL_HEALTH_SUMMARY_PATH,
        MONTHLY_AGGREGATION_PATH,
        MONTHLY_SUMMARY_PATH,
        PROCESSED_TRANSACTIONS_PATH,
    )
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from src.config import (
        ANALYSIS_OUTPUTS_DIR,
        BUDGET_SUMMARY_PATH,
        CATEGORY_SUMMARY_PATH,
        EXPENSE_GROUP_SUMMARY_PATH,
        FINANCIAL_HEALTH_SUMMARY_PATH,
        MONTHLY_AGGREGATION_PATH,
        MONTHLY_SUMMARY_PATH,
        PROCESSED_TRANSACTIONS_PATH,
    )


FINANCIAL_TRANSACTION_TYPES = {
    "income": "total_income",
    "expense": "total_expenses",
    "savings": "total_savings",
    "debt payment": "total_debt_payments",
}


def _require_analysis_columns(df, required_columns, dataset_name):
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise KeyError(
            f"{dataset_name} is missing required columns: "
            + ", ".join(missing_columns)
        )


def _as_number(series):
    return pd.to_numeric(series, errors="coerce").fillna(0.0)


def _safe_divide(numerator, denominator):
    if denominator == 0 or pd.isna(denominator):
        return None
    return float(numerator / denominator)


def _clamp_score(value):
    if value is None or pd.isna(value):
        return 0.0
    return min(max(float(value), 0.0), 100.0)


def _round_value(value, digits=2):
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def _json_ready(value):
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if np.isnan(value) else float(value)
    if pd.isna(value):
        return None
    return value


def _records(df):
    return _json_ready(df.to_dict(orient="records"))


def load_preprocessed_datasets(
    processed_path=PROCESSED_TRANSACTIONS_PATH,
    monthly_path=MONTHLY_AGGREGATION_PATH,
):
    """Load transaction-level and monthly aggregated preprocessing outputs."""
    transactions_df = pd.read_csv(processed_path)
    monthly_df = pd.read_csv(monthly_path)
    return transactions_df, monthly_df


def _prepare_processed_transactions(transactions_df):
    required_columns = [
        "year_month",
        "transaction_type",
        "category",
        "actual_amount",
        "budget_amount",
    ]
    _require_analysis_columns(transactions_df, required_columns, "processed dataset")

    processed_df = transactions_df.copy()
    processed_df["actual_amount"] = _as_number(processed_df["actual_amount"])
    processed_df["budget_amount"] = _as_number(processed_df["budget_amount"])
    processed_df["transaction_type_normalized"] = (
        processed_df["transaction_type"].astype(str).str.strip().str.lower()
    )
    return processed_df


def _prepare_monthly_aggregation(monthly_df):
    required_columns = [
        "year_month",
        "total_income",
        "total_expenses",
        "total_savings",
        "total_debt_payments",
    ]
    _require_analysis_columns(monthly_df, required_columns, "monthly aggregated dataset")

    prepared_df = monthly_df.copy()
    for column in required_columns[1:]:
        prepared_df[column] = _as_number(prepared_df[column])
    prepared_df = prepared_df.sort_values("year_month").reset_index(drop=True)
    return prepared_df


def _monthly_financials(monthly_df):
    monthly = monthly_df[
        [
            "year_month",
            "total_income",
            "total_expenses",
            "total_savings",
            "total_debt_payments",
        ]
    ].copy()
    monthly["savings_rate"] = monthly.apply(
        lambda row: _safe_divide(row["total_savings"] * 100, row["total_income"]),
        axis=1,
    )
    monthly["income_to_expense_ratio"] = monthly.apply(
        lambda row: _safe_divide(row["total_income"], row["total_expenses"]),
        axis=1,
    )
    monthly["debt_ratio"] = monthly.apply(
        lambda row: _safe_divide(row["total_debt_payments"] * 100, row["total_income"]),
        axis=1,
    )

    numeric_columns = [
        "total_income",
        "total_expenses",
        "total_savings",
        "total_debt_payments",
        "savings_rate",
        "income_to_expense_ratio",
        "debt_ratio",
    ]
    monthly[numeric_columns] = monthly[numeric_columns].round(2)
    return monthly


def _top_spending_categories(processed_df):
    expense_df = processed_df[
        processed_df["transaction_type_normalized"] == "expense"
    ].copy()
    if expense_df.empty:
        return []

    category_spending = (
        expense_df.groupby("category", observed=True)
        .agg(
            total_spent=("actual_amount", "sum"),
            transaction_count=("transaction_id", "count")
            if "transaction_id" in expense_df.columns
            else ("actual_amount", "count"),
            average_transaction=("actual_amount", "mean"),
        )
        .sort_values("total_spent", ascending=False)
        .head(5)
        .reset_index()
    )
    category_spending[["total_spent", "average_transaction"]] = category_spending[
        ["total_spent", "average_transaction"]
    ].round(2)
    return _records(category_spending)


def _category_summary(processed_df):
    expense_df = processed_df[
        processed_df["transaction_type_normalized"] == "expense"
    ].copy()
    if expense_df.empty:
        return []

    category_summary = (
        expense_df.groupby("category", observed=True)
        .agg(
            total_spent=("actual_amount", "sum"),
            transaction_count=("actual_amount", "count"),
            average_transaction=("actual_amount", "mean"),
        )
        .reset_index()
    )
    total_spent = category_summary["total_spent"].sum()
    category_summary["pct_of_expenses"] = category_summary["total_spent"].apply(
        lambda value: _safe_divide(value * 100, total_spent)
    )
    category_summary = category_summary.sort_values(
        "total_spent", ascending=False
    ).reset_index(drop=True)
    numeric_columns = ["total_spent", "average_transaction", "pct_of_expenses"]
    category_summary[numeric_columns] = category_summary[numeric_columns].round(2)
    return _records(category_summary)


def _expense_group_summary(processed_df):
    expense_df = processed_df[
        processed_df["transaction_type_normalized"] == "expense"
    ].copy()
    if expense_df.empty:
        return []

    if "expense_group" in expense_df.columns:
        group_column = "expense_group"
    elif "necessity_type" in expense_df.columns:
        group_column = "necessity_type"
    else:
        return []

    expense_df[group_column] = expense_df[group_column].fillna("Unknown").astype(str)
    expense_group_summary = (
        expense_df.groupby(group_column, observed=True)
        .agg(
            total_spent=("actual_amount", "sum"),
            transaction_count=("actual_amount", "count"),
            average_transaction=("actual_amount", "mean"),
        )
        .reset_index()
        .rename(columns={group_column: "expense_group"})
    )
    total_spent = expense_group_summary["total_spent"].sum()
    expense_group_summary["pct_of_expenses"] = expense_group_summary[
        "total_spent"
    ].apply(lambda value: _safe_divide(value * 100, total_spent))
    expense_group_summary = expense_group_summary.sort_values(
        "total_spent", ascending=False
    ).reset_index(drop=True)
    numeric_columns = ["total_spent", "average_transaction", "pct_of_expenses"]
    expense_group_summary[numeric_columns] = expense_group_summary[
        numeric_columns
    ].round(2)
    return _records(expense_group_summary)


def _needs_wants_ratio(processed_df):
    expense_df = processed_df[processed_df["transaction_type_normalized"] == "expense"]
    if expense_df.empty:
        return {
            "needs_spending": 0.0,
            "wants_spending": 0.0,
            "needs_to_wants_ratio": None,
            "needs_percent": None,
            "wants_percent": None,
        }

    if "expense_group" in expense_df.columns:
        group_column = "expense_group"
    elif "necessity_type" in expense_df.columns:
        group_column = "necessity_type"
    else:
        group_column = None

    if group_column is None:
        return {
            "needs_spending": 0.0,
            "wants_spending": 0.0,
            "needs_to_wants_ratio": None,
            "needs_percent": None,
            "wants_percent": None,
            "classification_column": None,
        }

    groups = expense_df[group_column].astype(str).str.strip().str.lower()
    needs_spending = expense_df.loc[groups.eq("needs") | groups.eq("need"), "actual_amount"].sum()
    wants_spending = expense_df.loc[groups.eq("wants") | groups.eq("want"), "actual_amount"].sum()
    classified_total = needs_spending + wants_spending

    return {
        "classification_column": group_column,
        "needs_spending": _round_value(needs_spending),
        "wants_spending": _round_value(wants_spending),
        "needs_to_wants_ratio": _round_value(
            _safe_divide(needs_spending, wants_spending)
        ),
        "needs_percent": _round_value(
            _safe_divide(needs_spending * 100, classified_total)
        ),
        "wants_percent": _round_value(
            _safe_divide(wants_spending * 100, classified_total)
        ),
    }


def _budget_variance_by_category(processed_df):
    expense_df = processed_df[
        processed_df["transaction_type_normalized"] == "expense"
    ].copy()
    if expense_df.empty:
        return [], None

    monthly_category_budget = (
        expense_df.groupby(["year_month", "category"], observed=True)
        .agg(
            actual_spend=("actual_amount", "sum"),
            budget_amount=("budget_amount", "max"),
        )
        .reset_index()
    )
    category_budget = (
        monthly_category_budget.groupby("category", observed=True)
        .agg(
            total_spent=("actual_spend", "sum"),
            total_budget=("budget_amount", "sum"),
        )
        .reset_index()
    )
    category_budget["budget_variance"] = (
        category_budget["total_spent"] - category_budget["total_budget"]
    )
    category_budget["variance_percent"] = category_budget.apply(
        lambda row: _safe_divide(row["budget_variance"] * 100, row["total_budget"]),
        axis=1,
    )
    category_budget["status"] = np.where(
        category_budget["budget_variance"] > 0, "Overspent", "Within Budget"
    )
    category_budget = category_budget.sort_values(
        "budget_variance", ascending=False
    ).reset_index(drop=True)
    numeric_columns = [
        "total_spent",
        "total_budget",
        "budget_variance",
        "variance_percent",
    ]
    category_budget[numeric_columns] = category_budget[numeric_columns].round(2)

    overspending = category_budget[category_budget["budget_variance"] > 0]
    highest_overspending_category = (
        _json_ready(overspending.iloc[0].to_dict()) if not overspending.empty else None
    )
    return _records(category_budget), highest_overspending_category


def _monthly_emergency_fund_contributions(processed_df, monthly_df):
    savings_df = processed_df[
        processed_df["transaction_type_normalized"] == "savings"
    ].copy()
    if savings_df.empty:
        return pd.DataFrame(
            {"year_month": monthly_df["year_month"], "emergency_fund_contribution": 0.0}
        )

    searchable_columns = [
        column
        for column in ["category", "subcategory", "budget_category", "description"]
        if column in savings_df.columns
    ]
    emergency_mask = pd.Series(False, index=savings_df.index)
    for column in searchable_columns:
        emergency_mask = emergency_mask | savings_df[column].astype(str).str.contains(
            "emergency fund", case=False, na=False
        )

    emergency_fund = (
        savings_df[emergency_mask]
        .groupby("year_month", observed=True)["actual_amount"]
        .sum()
    )
    monthly_contributions = pd.DataFrame({"year_month": monthly_df["year_month"]})
    monthly_contributions["emergency_fund_contribution"] = (
        monthly_contributions["year_month"].map(emergency_fund).fillna(0.0)
    )
    return monthly_contributions


def _emergency_fund_consistency(processed_df, monthly_df):
    monthly_contributions = _monthly_emergency_fund_contributions(
        processed_df, monthly_df
    )

    active_months = int(
        (monthly_contributions["emergency_fund_contribution"] > 0).sum()
    )
    total_months = int(len(monthly_contributions))
    contribution_values = monthly_contributions["emergency_fund_contribution"]

    monthly_contributions["emergency_fund_contribution"] = contribution_values.round(2)
    return {
        "months_with_contribution": active_months,
        "months_observed": total_months,
        "consistency_rate_percent": _round_value(
            _safe_divide(active_months * 100, total_months)
        ),
        "average_monthly_contribution": _round_value(contribution_values.mean()),
        "median_monthly_contribution": _round_value(contribution_values.median()),
        "standard_deviation": _round_value(contribution_values.std()),
        "minimum_monthly_contribution": _round_value(contribution_values.min()),
        "maximum_monthly_contribution": _round_value(contribution_values.max()),
        "monthly_contributions": _records(monthly_contributions),
    }


def _financial_health_score_summary(processed_df, monthly_df, monthly_financials):
    expense_df = processed_df[processed_df["transaction_type_normalized"] == "expense"]
    group_column = None
    if "expense_group" in expense_df.columns:
        group_column = "expense_group"
    elif "necessity_type" in expense_df.columns:
        group_column = "necessity_type"

    monthly_scores = monthly_financials[
        [
            "year_month",
            "total_income",
            "total_expenses",
            "total_savings",
            "total_debt_payments",
            "savings_rate",
            "debt_ratio",
        ]
    ].copy()

    if group_column:
        groups = expense_df[group_column].astype(str).str.strip().str.lower()
        needs_spending = (
            expense_df[groups.eq("needs") | groups.eq("need")]
            .groupby("year_month", observed=True)["actual_amount"]
            .sum()
        )
        wants_spending = (
            expense_df[groups.eq("wants") | groups.eq("want")]
            .groupby("year_month", observed=True)["actual_amount"]
            .sum()
        )
    else:
        needs_spending = pd.Series(dtype="float64")
        wants_spending = pd.Series(dtype="float64")

    emergency_fund = _monthly_emergency_fund_contributions(processed_df, monthly_df)
    monthly_scores["needs_spending"] = (
        monthly_scores["year_month"].map(needs_spending).fillna(0.0)
    )
    monthly_scores["wants_spending"] = (
        monthly_scores["year_month"].map(wants_spending).fillna(0.0)
    )
    monthly_scores["emergency_fund_contribution"] = (
        monthly_scores["year_month"]
        .map(emergency_fund.set_index("year_month")["emergency_fund_contribution"])
        .fillna(0.0)
    )

    # Convert Needs, Wants, and Savings amounts into income-based percentages
    # so the 50/30/20 rule can be compared month by month.
    monthly_scores["needs_percent"] = monthly_scores.apply(
        lambda row: _safe_divide(row["needs_spending"] * 100, row["total_income"]),
        axis=1,
    )
    monthly_scores["wants_percent"] = monthly_scores.apply(
        lambda row: _safe_divide(row["wants_spending"] * 100, row["total_income"]),
        axis=1,
    )
    monthly_scores["savings_percent"] = monthly_scores["savings_rate"]

    # Savings Score rewards progress toward a 15% target savings rate.
    monthly_scores["savings_score"] = (
        (monthly_scores["savings_rate"].fillna(0.0) / 15.0) * 100.0
    ).clip(0, 100)

    # Debt Score applies the requested DTI formula, where lower debt burden
    # produces a higher score and scores are clamped at zero.
    monthly_scores["debt_score"] = (
        100.0 - ((monthly_scores["debt_ratio"].fillna(0.0) / 36.0) * 100.0)
    ).clip(0, 100)

    # Budget Balance Score subtracts total percentage-point deviation from
    # the 50% Needs, 30% Wants, and 20% Savings targets.
    monthly_scores["budget_balance_deviation"] = (
        (monthly_scores["needs_percent"].fillna(0.0) - 50.0).abs()
        + (monthly_scores["wants_percent"].fillna(0.0) - 30.0).abs()
        + (monthly_scores["savings_percent"].fillna(0.0) - 20.0).abs()
    )
    monthly_scores["budget_balance_score"] = (
        100.0 - monthly_scores["budget_balance_deviation"]
    ).clip(0, 100)

    # Emergency Fund Score is binary for each month: 100 when an emergency
    # fund contribution exists, otherwise 0.
    monthly_scores["emergency_fund_score"] = np.where(
        monthly_scores["emergency_fund_contribution"] > 0, 100.0, 0.0
    )

    # Final score is the weighted sum of all four clamped component scores.
    monthly_scores["financial_health_score"] = (
        (monthly_scores["savings_score"].apply(_clamp_score) * 0.30)
        + (monthly_scores["debt_score"].apply(_clamp_score) * 0.30)
        + (monthly_scores["budget_balance_score"].apply(_clamp_score) * 0.25)
        + (monthly_scores["emergency_fund_score"].apply(_clamp_score) * 0.15)
    ).clip(0, 100)

    score_columns = [
        "needs_spending",
        "wants_spending",
        "emergency_fund_contribution",
        "needs_percent",
        "wants_percent",
        "savings_percent",
        "savings_score",
        "debt_score",
        "budget_balance_deviation",
        "budget_balance_score",
        "emergency_fund_score",
        "financial_health_score",
    ]
    monthly_scores[score_columns] = monthly_scores[score_columns].round(2)
    final_scores = monthly_scores["financial_health_score"]

    return {
        "status": "calculated",
        "pending_formula": (
            "financial_health_score = (savings_score * 0.30) + "
            "(debt_score * 0.30) + (budget_balance_score * 0.25) + "
            "(emergency_fund_score * 0.15). Savings Score = "
            "min((savings_rate / 15) * 100, 100). Debt Score = "
            "max(0, 100 - ((dti / 36) * 100)). Budget Balance Score = "
            "clamp(100 - (abs(needs_percent - 50) + abs(wants_percent - 30) "
            "+ abs(savings_percent - 20)), 0, 100). Emergency Fund Score = "
            "100 when the month has an emergency fund contribution, else 0."
        ),
        "component_weights": {
            "savings_score": 0.30,
            "debt_score": 0.30,
            "budget_balance_score": 0.25,
            "emergency_fund_score": 0.15,
        },
        "targets": {
            "savings_rate_percent": 15.0,
            "debt_to_income_ratio_percent": 36.0,
            "needs_percent": 50.0,
            "wants_percent": 30.0,
            "savings_percent": 20.0,
        },
        "classification_column": group_column,
        "average_financial_health_score": _round_value(final_scores.mean()),
        "minimum_financial_health_score": _round_value(final_scores.min()),
        "maximum_financial_health_score": _round_value(final_scores.max()),
        "monthly_scores": _records(monthly_scores),
    }


def analyze_preprocessed_finances(transactions_df, monthly_df):
    """Compute financial metrics from preprocessed transaction and monthly data."""
    processed_df = _prepare_processed_transactions(transactions_df)
    monthly = _prepare_monthly_aggregation(monthly_df)
    monthly_financials = _monthly_financials(monthly)

    totals = {
        column: _round_value(monthly[column].sum())
        for column in FINANCIAL_TRANSACTION_TYPES.values()
    }
    total_transactions = int(len(processed_df))
    transaction_amounts = processed_df["actual_amount"]

    budget_variance, highest_overspending_category = _budget_variance_by_category(
        processed_df
    )

    analysis = {
        "dataset_overview": {
            "processed_transaction_rows": total_transactions,
            "monthly_aggregated_rows": int(len(monthly)),
            "months_observed": int(monthly["year_month"].nunique()),
            "first_month": monthly["year_month"].min(),
            "last_month": monthly["year_month"].max(),
        },
        "totals": {
            "total_income": totals["total_income"],
            "total_expenses": totals["total_expenses"],
            "total_savings": totals["total_savings"],
            "total_debt_payments": totals["total_debt_payments"],
        },
        "monthly_income_expenses_savings_debt_payments": _records(
            monthly_financials
        ),
        "statistical_analysis": {
            "average_monthly_expense": _round_value(monthly["total_expenses"].mean()),
            "median_transaction_amount": _round_value(transaction_amounts.median()),
            "standard_deviation_of_monthly_expenses": _round_value(
                monthly["total_expenses"].std()
            ),
        },
        "category_summary": _category_summary(processed_df),
        "top_5_spending_categories": _top_spending_categories(processed_df),
        "expense_group_summary": _expense_group_summary(processed_df),
        "needs_vs_wants_spending_ratio": _needs_wants_ratio(processed_df),
        "savings_rate_per_month": _records(
            monthly_financials[["year_month", "savings_rate"]]
        ),
        "income_to_expense_ratio_per_month": _records(
            monthly_financials[["year_month", "income_to_expense_ratio"]]
        ),
        "debt_ratio_per_month": _records(
            monthly_financials[["year_month", "debt_ratio"]]
        ),
        "budget_variance_per_category": budget_variance,
        "highest_overspending_category": highest_overspending_category,
        "emergency_fund_contribution_consistency": _emergency_fund_consistency(
            processed_df, monthly
        ),
        "financial_health_score_summary": _financial_health_score_summary(
            processed_df, monthly, monthly_financials
        ),
    }
    return _json_ready(analysis)


def get_preprocessed_financial_analysis(
    processed_path=PROCESSED_TRANSACTIONS_PATH,
    monthly_path=MONTHLY_AGGREGATION_PATH,
):
    """Load preprocessed outputs and return the project financial analysis."""
    transactions_df, monthly_df = load_preprocessed_datasets(
        processed_path=processed_path,
        monthly_path=monthly_path,
    )
    return analyze_preprocessed_finances(transactions_df, monthly_df)


def save_analysis_summaries(
    analysis=None,
    processed_path=PROCESSED_TRANSACTIONS_PATH,
    monthly_path=MONTHLY_AGGREGATION_PATH,
):
    """Save computed analysis summaries to data/outputs/processed/analysis."""
    if analysis is None:
        analysis = get_preprocessed_financial_analysis(
            processed_path=processed_path,
            monthly_path=monthly_path,
        )

    ANALYSIS_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    financial_health = analysis.get("financial_health_score_summary", {})
    exports = {
        "monthly_summary": (
            pd.DataFrame(
                analysis.get("monthly_income_expenses_savings_debt_payments", [])
            ),
            MONTHLY_SUMMARY_PATH,
        ),
        "category_summary": (
            pd.DataFrame(analysis.get("category_summary", [])),
            CATEGORY_SUMMARY_PATH,
        ),
        "expense_group_summary": (
            pd.DataFrame(analysis.get("expense_group_summary", [])),
            EXPENSE_GROUP_SUMMARY_PATH,
        ),
        "budget_variance_summary": (
            pd.DataFrame(analysis.get("budget_variance_per_category", [])),
            BUDGET_SUMMARY_PATH,
        ),
        "financial_health_summary": (
            pd.DataFrame(financial_health.get("monthly_scores", [])),
            FINANCIAL_HEALTH_SUMMARY_PATH,
        ),
    }

    written_paths = {}
    for name, (summary_df, path) in exports.items():
        summary_df.to_csv(path, index=False)
        written_paths[name] = path

    return written_paths


def get_basic_summary(df):
    """Return summary statistics and grouped analysis for the dashboard."""
    summary = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
    }

    if "amount_php" not in df.columns:
        return summary

    analysis_df = df.copy()
    analysis_df["amount_php"] = pd.to_numeric(
        analysis_df["amount_php"], errors="coerce"
    )
    amount_values = analysis_df["amount_php"].dropna()
    expense_values = amount_values[amount_values > 0]
    refund_values = amount_values[amount_values < 0]
    amount_mode = amount_values.mode()

    net_amount = float(amount_values.sum())
    gross_expense_total = float(expense_values.sum())
    refund_total = float(abs(refund_values.sum()))

    summary["total_transactions"] = int(amount_values.count())
    summary["expense_transactions"] = int(expense_values.count())
    summary["refund_transactions"] = int(refund_values.count())
    summary["net_amount"] = net_amount
    summary["gross_expense_total"] = gross_expense_total
    summary["refund_total"] = refund_total
    summary["total_expense"] = net_amount
    summary["average_transaction"] = (
        float(amount_values.mean()) if not amount_values.empty else None
    )
    summary["average_expense"] = (
        float(expense_values.mean()) if not expense_values.empty else None
    )

    summary["amount_statistics"] = {
        "mean": float(amount_values.mean()) if not amount_values.empty else None,
        "median": float(amount_values.median()) if not amount_values.empty else None,
        "mode": float(amount_mode.iloc[0]) if not amount_mode.empty else None,
        "min": float(amount_values.min()) if not amount_values.empty else None,
        "max": float(amount_values.max()) if not amount_values.empty else None,
        "largest_refund": float(refund_values.min()) if not refund_values.empty else None,
        "largest_refund_abs": float(abs(refund_values.min()))
        if not refund_values.empty
        else None,
        "largest_transaction": float(amount_values.max()) if not amount_values.empty else None,
        "standard_deviation": float(amount_values.std())
        if not amount_values.empty
        else None,
    }

    numeric_columns = analysis_df.select_dtypes(include="number").columns.tolist()
    if len(numeric_columns) >= 2:
        correlation_matrix = analysis_df[numeric_columns].corr().round(4)
        summary["correlation_analysis"] = {
            "numeric_columns": numeric_columns,
            "matrix": correlation_matrix.where(
                pd.notna(correlation_matrix), None
            ).to_dict(),
            "amount_correlations": correlation_matrix["amount_php"]
            .drop(labels=["amount_php"], errors="ignore")
            .dropna()
            .sort_values(key=lambda values: values.abs(), ascending=False)
            .to_dict()
            if "amount_php" in correlation_matrix.columns
            else {},
        }
    else:
        summary["correlation_analysis"] = {
            "numeric_columns": numeric_columns,
            "matrix": {},
            "amount_correlations": {},
        }

    excluded_frequency_columns = {"transaction_id", "notes"}
    categorical_columns = [
        column
        for column in analysis_df.select_dtypes(
            include=["object", "category"]
        ).columns.tolist()
        if column not in excluded_frequency_columns
    ]
    frequency_distributions = {}
    for column in categorical_columns:
        value_counts = (
            analysis_df[column]
            .astype(object)
            .fillna("Unknown")
            .astype(str)
            .value_counts()
        )
        percentages = (value_counts / len(analysis_df) * 100).round(2)
        frequency_distributions[column] = {
            value: {
                "count": int(count),
                "percentage": float(percentages.loc[value]),
            }
            for value, count in value_counts.items()
        }
    summary["frequency_distributions"] = frequency_distributions

    if "category" in analysis_df.columns:
        category_totals = (
            analysis_df.dropna(subset=["amount_php"])
            .query("amount_php > 0")
            .groupby("category", observed=True)["amount_php"]
            .sum()
            .sort_values(ascending=False)
        )
        summary["category_totals"] = category_totals.round(2).to_dict()

        category_net_totals = (
            analysis_df.dropna(subset=["amount_php"])
            .groupby("category", observed=True)["amount_php"]
            .sum()
            .sort_values(ascending=False)
        )
        summary["category_net_totals"] = category_net_totals.round(2).to_dict()

    if "month" in analysis_df.columns:
        month_values = analysis_df["month"].astype(str)
    elif "date" in analysis_df.columns:
        date_values = pd.to_datetime(analysis_df["date"], errors="coerce")
        month_values = date_values.dt.to_period("M").astype(str)
    else:
        month_values = None

    if month_values is not None:
        monthly_df = analysis_df.assign(month=month_values).dropna(
            subset=["month", "amount_php"]
        )
        monthly_df = monthly_df[monthly_df["month"].astype(str) != "NaT"]
        monthly_trends = (
            monthly_df.groupby("month")["amount_php"]
            .agg(
                total="sum",
                net_amount="sum",
                average="mean",
                average_transaction="mean",
                transaction_count="count",
            )
            .sort_index()
            .round(2)
        )
        monthly_expenses = (
            monthly_df[monthly_df["amount_php"] > 0]
            .groupby("month", observed=True)["amount_php"]
            .sum()
        )
        monthly_refunds = (
            monthly_df[monthly_df["amount_php"] < 0]
            .groupby("month", observed=True)["amount_php"]
            .sum()
            .abs()
        )
        monthly_trends["gross_expense_total"] = (
            monthly_trends.index.to_series().map(monthly_expenses).fillna(0).round(2)
        )
        monthly_trends["refund_total"] = (
            monthly_trends.index.to_series().map(monthly_refunds).fillna(0).round(2)
        )
        summary["monthly_trends"] = monthly_trends.to_dict(orient="index")

    if "budget_limit_php" in analysis_df.columns:
        analysis_df["budget_limit_php"] = pd.to_numeric(
            analysis_df["budget_limit_php"], errors="coerce"
        ).fillna(0)
        expense_total = gross_expense_total

        if "category" in analysis_df.columns and month_values is not None:
            budget_df = analysis_df.assign(month=month_values)
            budget_df = budget_df[budget_df["month"].astype(str) != "NaT"]
            budget_scope = ["category", "month"]
        elif "category" in analysis_df.columns:
            budget_df = analysis_df.copy()
            budget_scope = ["category"]
        else:
            budget_df = analysis_df.copy()
            budget_scope = None

        if budget_scope:
            unique_budgets = (
                budget_df.groupby(budget_scope, observed=True)["budget_limit_php"]
                .max()
                .reset_index()
            )
            budget_total = unique_budgets["budget_limit_php"].sum()
        else:
            budget_total = budget_df["budget_limit_php"].sum()

        summary["budget_summary"] = {
            "total_budget": float(budget_total),
            "total_spent": float(expense_total),
            "total_expenses": float(expense_total),
            "remaining_budget": float(budget_total - expense_total),
            "budget_usage_percent": float((expense_total / budget_total) * 100)
            if budget_total
            else 0.0,
            "budget_basis": "category_month" if budget_scope == ["category", "month"] else "category",
        }

        if "category" in analysis_df.columns:
            category_expenses = (
                analysis_df[analysis_df["amount_php"] > 0]
                .groupby("category", observed=True)["amount_php"]
                .sum()
            )
            if "month" in budget_df.columns:
                category_budgets = (
                    budget_df.groupby(["category", "month"], observed=True)["budget_limit_php"]
                    .max()
                    .groupby("category", observed=True)
                    .sum()
                )
            else:
                category_budgets = budget_df.groupby("category", observed=True)[
                    "budget_limit_php"
                ].max()

            category_budget = pd.DataFrame(
                {
                    "total_spent": category_expenses,
                    "total_budget": category_budgets,
                }
            ).fillna(0)
            category_budget["remaining_budget"] = (
                category_budget["total_budget"] - category_budget["total_spent"]
            )
            category_budget["usage_percent"] = category_budget.apply(
                lambda row: (row["total_spent"] / row["total_budget"]) * 100
                if row["total_budget"]
                else 0.0,
                axis=1,
            )
            summary["budget_by_category"] = (
                category_budget.round(2)
                .sort_values("usage_percent", ascending=False)
                .to_dict(orient="index")
            )

    return summary


if __name__ == "__main__":
    financial_analysis = get_preprocessed_financial_analysis()
    saved_paths = save_analysis_summaries(financial_analysis)
    print(json.dumps(financial_analysis, indent=2))
    print("Saved analysis summaries:")
    for name, path in saved_paths.items():
        print(f"{name}: {path}")
