from pathlib import Path

import pandas as pd

from src.config import (
    BUDGET_SUMMARY_PATH,
    CATEGORY_SUMMARY_PATH,
    MONTHLY_SUMMARY_PATH,
    OUTPUTS_DIR,
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


def _build_category_summary(export_df):
    if export_df is None or "category" not in export_df.columns:
        return pd.DataFrame(
            columns=[
                "category",
                "total_spent",
                "average_spent",
                "transaction_count",
                "pct_of_total",
            ]
        )

    grouped = (
        export_df.groupby("category", observed=True)["amount_php"]
        .agg(total_spent="sum", average_spent="mean", transaction_count="count")
        .reset_index()
    )
    total = grouped["total_spent"].sum()
    grouped["pct_of_total"] = (
        (grouped["total_spent"] / total * 100).round(1) if total else 0.0
    )
    grouped["total_spent"] = grouped["total_spent"].round(2)
    grouped["average_spent"] = grouped["average_spent"].round(2)
    return grouped.sort_values("total_spent", ascending=False)


def _build_monthly_summary(export_df):
    if export_df is None or "month" not in export_df.columns:
        return pd.DataFrame(
            columns=["month", "total_spent", "average_spent", "transaction_count"]
        )

    monthly = (
        export_df.dropna(subset=["month"])
        .groupby("month")["amount_php"]
        .agg(total_spent="sum", average_spent="mean", transaction_count="count")
        .reset_index()
        .sort_values("month")
    )
    monthly["total_spent"] = monthly["total_spent"].round(2)
    monthly["average_spent"] = monthly["average_spent"].round(2)
    return monthly


def _build_payment_summary(export_df):
    if export_df is None or "payment_method" not in export_df.columns:
        return pd.DataFrame(
            columns=[
                "payment_method",
                "total_spent",
                "transaction_count",
                "pct_of_total",
            ]
        )

    grouped = (
        export_df.groupby("payment_method", observed=True)["amount_php"]
        .agg(total_spent="sum", transaction_count="count")
        .reset_index()
    )
    total = grouped["total_spent"].sum()
    grouped["pct_of_total"] = (
        (grouped["total_spent"] / total * 100).round(1) if total else 0.0
    )
    grouped["total_spent"] = grouped["total_spent"].round(2)
    return grouped.sort_values("total_spent", ascending=False)


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

    budget = (
        export_df.groupby("category", observed=True)
        .agg(
            total_spent=("amount_php", "sum"),
            total_budget=("budget_limit_php", "sum"),
        )
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
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
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
