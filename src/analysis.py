import pandas as pd


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
    amount_mode = amount_values.mode()

    summary["total_transactions"] = int(amount_values.count())
    summary["total_expense"] = float(amount_values.sum())
    summary["average_expense"] = (
        float(amount_values.mean()) if not amount_values.empty else None
    )

    summary["amount_statistics"] = {
        "mean": float(amount_values.mean()) if not amount_values.empty else None,
        "median": float(amount_values.median()) if not amount_values.empty else None,
        "mode": float(amount_mode.iloc[0]) if not amount_mode.empty else None,
        "min": float(amount_values.min()) if not amount_values.empty else None,
        "max": float(amount_values.max()) if not amount_values.empty else None,
        "standard_deviation": float(amount_values.std())
        if not amount_values.empty
        else None,
    }

    if "category" in analysis_df.columns:
        category_totals = (
            analysis_df.dropna(subset=["amount_php"])
            .groupby("category", observed=True)["amount_php"]
            .sum()
            .sort_values(ascending=False)
        )
        summary["category_totals"] = category_totals.round(2).to_dict()

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
        monthly_trends = (
            monthly_df.groupby("month")["amount_php"]
            .agg(total="sum", average="mean", transaction_count="count")
            .sort_index()
            .round(2)
        )
        summary["monthly_trends"] = monthly_trends.to_dict(orient="index")

    if "budget_limit_php" in analysis_df.columns:
        analysis_df["budget_limit_php"] = pd.to_numeric(
            analysis_df["budget_limit_php"], errors="coerce"
        ).fillna(0)
        budget_total = analysis_df["budget_limit_php"].sum()
        expense_total = amount_values.sum()
        summary["budget_summary"] = {
            "total_budget": float(budget_total),
            "total_spent": float(expense_total),
            "remaining_budget": float(budget_total - expense_total),
            "budget_usage_percent": float((expense_total / budget_total) * 100)
            if budget_total
            else 0.0,
        }

        if "category" in analysis_df.columns:
            category_budget = (
                analysis_df.groupby("category", observed=True)
                .agg(
                    total_spent=("amount_php", "sum"),
                    total_budget=("budget_limit_php", "sum"),
                )
                .round(2)
            )
            category_budget["remaining_budget"] = (
                category_budget["total_budget"] - category_budget["total_spent"]
            ).round(2)
            summary["budget_by_category"] = category_budget.to_dict(orient="index")

    return summary
