from pathlib import Path

import pandas as pd

from src.config import (
    ANALYSIS_OUTPUTS_DIR,
    BUDGET_SUMMARY_PATH,
    CATEGORY_SUMMARY_PATH,
    MONTHLY_SUMMARY_PATH,
    PAYMENT_SUMMARY_PATH,
)


def _prepare_export_df(df):
    """Return a numeric-ready copy for summary exports."""
    if df is None or df.empty:
        return None

    export_df = df.copy()
    export_df["amount_php"] = pd.to_numeric(export_df["amount_php"], errors="coerce")
    export_df = export_df.dropna(subset=["amount_php"])
    if export_df.empty:
        return None

    if "budget_limit_php" in export_df.columns:
        export_df["budget_limit_php"] = pd.to_numeric(
            export_df["budget_limit_php"], errors="coerce"
        ).fillna(0)

    if "month" in export_df.columns:
        export_df["month"] = export_df["month"].astype(str)
    elif "date" in export_df.columns:
        export_df["month"] = (
            pd.to_datetime(export_df["date"], errors="coerce")
            .dt.to_period("M")
            .astype(str)
        )

    return export_df


def _expense_rows(df):
    mask = df["amount_php"] > 0
    if "transaction_type" in df.columns:
        transaction_type = df["transaction_type"].astype(str).str.strip().str.lower()
        mask &= transaction_type == "expense"
    elif "category" in df.columns:
        category = df["category"].astype(str).str.strip().str.lower()
        mask &= category != "income"
    return df[mask].copy()


def _build_category_summary(export_df):
    if export_df is None or "category" not in export_df.columns:
        return pd.DataFrame(
            columns=[
                "category",
                "total_expenses",
                "average_expense",
                "transaction_count",
                "pct_of_total",
            ]
        )

    expense_df = _expense_rows(export_df)
    grouped = (
        expense_df.groupby("category", observed=True)["amount_php"]
        .agg(total_expenses="sum", average_expense="mean", transaction_count="count")
        .reset_index()
    )
    total = grouped["total_expenses"].sum()
    grouped["pct_of_total"] = (
        (grouped["total_expenses"] / total * 100).round(1) if total else 0.0
    )
    grouped["total_expenses"] = grouped["total_expenses"].round(2)
    grouped["average_expense"] = grouped["average_expense"].round(2)
    return grouped.sort_values("total_expenses", ascending=False)


def _build_monthly_summary(export_df):
    if export_df is None or "month" not in export_df.columns:
        return pd.DataFrame(
            columns=[
                "month",
                "total_expenses",
                "refund_total",
                "net_spending",
                "cash_flow_total",
                "average_transaction",
                "transaction_count",
            ]
        )

    monthly_df = export_df.dropna(subset=["month"])
    monthly = (
        monthly_df.groupby("month")["amount_php"]
        .agg(cash_flow_total="sum", average_transaction="mean", transaction_count="count")
        .reset_index()
        .sort_values("month")
    )
    monthly_expenses = (
        _expense_rows(monthly_df).groupby("month")["amount_php"].sum()
    )
    monthly_refunds = (
        monthly_df[monthly_df["amount_php"] < 0]
        .groupby("month")["amount_php"]
        .sum()
        .abs()
    )
    monthly["total_expenses"] = monthly["month"].map(monthly_expenses).fillna(0)
    monthly["refund_total"] = monthly["month"].map(monthly_refunds).fillna(0)
    monthly["net_spending"] = monthly["total_expenses"] - monthly["refund_total"]
    monthly["cash_flow_total"] = monthly["cash_flow_total"].round(2)
    monthly["average_transaction"] = monthly["average_transaction"].round(2)
    monthly["total_expenses"] = monthly["total_expenses"].round(2)
    monthly["refund_total"] = monthly["refund_total"].round(2)
    monthly["net_spending"] = monthly["net_spending"].round(2)
    return monthly


def _build_payment_summary(export_df):
    if export_df is None or "payment_method" not in export_df.columns:
        return pd.DataFrame(
            columns=[
                "payment_method",
                "total_expenses",
                "transaction_count",
                "pct_of_total",
            ]
        )

    expense_df = _expense_rows(export_df)
    grouped = (
        expense_df.groupby("payment_method", observed=True)["amount_php"]
        .agg(total_expenses="sum", transaction_count="count")
        .reset_index()
    )
    total = grouped["total_expenses"].sum()
    grouped["pct_of_total"] = (
        (grouped["total_expenses"] / total * 100).round(1) if total else 0.0
    )
    grouped["total_expenses"] = grouped["total_expenses"].round(2)
    return grouped.sort_values("total_expenses", ascending=False)


def _build_budget_summary(export_df):
    if export_df is None or "category" not in export_df.columns:
        return pd.DataFrame(
            columns=[
                "category",
                "total_spent",
                "total_budget",
                "remaining_budget",
                "usage_percent",
            ]
        )

    expense_totals = (
        _expense_rows(export_df)
        .groupby("category", observed=True)["amount_php"]
        .sum()
    )
    if "month" in export_df.columns:
        budget_df = _expense_rows(export_df)
        budget_totals = (
            budget_df.groupby(["category", "month"], observed=True)["budget_limit_php"]
            .max()
            .groupby("category", observed=True)
            .sum()
        )
    else:
        budget_df = _expense_rows(export_df)
        budget_totals = budget_df.groupby("category", observed=True)[
            "budget_limit_php"
        ].max()

    budget = (
        pd.DataFrame(
            {
                "total_spent": expense_totals,
                "total_budget": budget_totals,
            }
        )
        .fillna(0)
        .reset_index()
    )
    budget["remaining_budget"] = (
        budget["total_budget"] - budget["total_spent"]
    ).round(2)
    budget["usage_percent"] = budget.apply(
        lambda row: round((row["total_spent"] / row["total_budget"]) * 100, 1)
        if row["total_budget"]
        else 0.0,
        axis=1,
    )
    budget["total_spent"] = budget["total_spent"].round(2)
    budget["total_budget"] = budget["total_budget"].round(2)
    return budget.sort_values("total_spent", ascending=False)


def export_summary_csvs(df):
    """Build and write summary CSV files from the filtered dataset."""
    ANALYSIS_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    export_df = _prepare_export_df(df)

    exports = {
        "Category summary": (_build_category_summary(export_df), CATEGORY_SUMMARY_PATH),
        "Monthly summary": (_build_monthly_summary(export_df), MONTHLY_SUMMARY_PATH),
        "Payment summary": (_build_payment_summary(export_df), PAYMENT_SUMMARY_PATH),
        "Budget summary": (_build_budget_summary(export_df), BUDGET_SUMMARY_PATH),
    }

    written_paths = {}
    for name, (summary_df, path) in exports.items():
        summary_df.to_csv(path, index=False)
        written_paths[name] = path

    return written_paths
