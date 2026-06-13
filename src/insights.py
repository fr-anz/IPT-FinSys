import pandas as pd


def _format_php(value):
    """Format a numeric value as a peso amount for insight text."""
    if value is None or pd.isna(value):
        return "PHP 0.00"
    return f"PHP {value:,.2f}"


def _prepare_insight_data(df):
    """Return a cleaned copy for insight calculations."""
    if df is None or df.empty or "amount_php" not in df.columns:
        return None

    insight_df = df.copy()
    insight_df["amount_php"] = pd.to_numeric(insight_df["amount_php"], errors="coerce")
    insight_df = insight_df.dropna(subset=["amount_php"])

    if insight_df.empty:
        return None

    if "date" in insight_df.columns:
        insight_df["date"] = pd.to_datetime(insight_df["date"], errors="coerce")

    if "month" in insight_df.columns:
        insight_df["month"] = insight_df["month"].astype(str)
    elif "date" in insight_df.columns:
        insight_df["month"] = insight_df["date"].dt.to_period("M").astype(str)

    if "budget_limit_php" in insight_df.columns:
        insight_df["budget_limit_php"] = pd.to_numeric(
            insight_df["budget_limit_php"], errors="coerce"
        ).fillna(0)

    return insight_df


def generate_insights(df):
    """Generate findings, trends, recommendations, and conclusion text."""
    insight_df = _prepare_insight_data(df)
    if insight_df is None:
        return ["No insight can be generated because the selected data is empty."]

    insights = []
    total_spent = insight_df["amount_php"].sum()
    average_spent = insight_df["amount_php"].mean()

    insights.append(
        f"Finding: The selected data contains {len(insight_df):,} transactions with a total recorded amount of {_format_php(total_spent)} and an average transaction amount of {_format_php(average_spent)}."
    )

    if "category" in insight_df.columns:
        category_totals = (
            insight_df.groupby("category", observed=True)["amount_php"]
            .sum()
            .sort_values(ascending=False)
        )
        top_category = category_totals.index[0]
        top_category_total = category_totals.iloc[0]
        category_share = (top_category_total / total_spent) * 100 if total_spent else 0
        insights.append(
            f"Finding: {top_category} is the highest spending category at {_format_php(top_category_total)}, which represents {category_share:.1f}% of the selected total."
        )

    if "month" in insight_df.columns:
        monthly_totals = (
            insight_df.groupby("month")["amount_php"].sum().sort_values(ascending=False)
        )
        peak_month = monthly_totals.index[0]
        peak_month_total = monthly_totals.iloc[0]
        insights.append(
            f"Trend: Spending is highest in {peak_month}, with {_format_php(peak_month_total)} recorded for that month."
        )

        chronological_totals = insight_df.groupby("month")["amount_php"].sum().sort_index()
        if len(chronological_totals) >= 2:
            first_month_total = chronological_totals.iloc[0]
            latest_month_total = chronological_totals.iloc[-1]
            change = latest_month_total - first_month_total
            direction = "increased" if change >= 0 else "decreased"
            insights.append(
                f"Trend: From the first to the latest available month, total spending {direction} by {_format_php(abs(change))}."
            )

    if "necessity_type" in insight_df.columns:
        necessity_totals = (
            insight_df.groupby("necessity_type", observed=True)["amount_php"]
            .sum()
            .sort_values(ascending=False)
        )
        top_necessity = necessity_totals.index[0]
        insights.append(
            f"Finding: {top_necessity} expenses account for the largest necessity-type total at {_format_php(necessity_totals.iloc[0])}."
        )

    if "payment_method" in insight_df.columns:
        payment_counts = insight_df["payment_method"].astype(str).value_counts()
        top_payment = payment_counts.index[0]
        insights.append(
            f"Finding: {top_payment} is the most frequently used payment method, appearing in {payment_counts.iloc[0]:,} transactions."
        )

    if "budget_limit_php" in insight_df.columns:
        total_budget = insight_df["budget_limit_php"].sum()
        remaining_budget = total_budget - total_spent
        budget_usage = (total_spent / total_budget) * 100 if total_budget else 0
        insights.append(
            f"Finding: The selected records used {budget_usage:.1f}% of the total budget, leaving {_format_php(remaining_budget)}."
        )

        if "category" in insight_df.columns:
            budget_by_category = insight_df.groupby("category", observed=True).agg(
                spent=("amount_php", "sum"),
                budget=("budget_limit_php", "sum"),
            )
            budget_by_category["usage_percent"] = budget_by_category.apply(
                lambda row: (row["spent"] / row["budget"]) * 100
                if row["budget"]
                else 0,
                axis=1,
            )
            highest_usage = budget_by_category.sort_values(
                "usage_percent", ascending=False
            ).iloc[0]
            insights.append(
                f"Recommendation: Review the {highest_usage.name} budget first because it has the highest budget usage at {highest_usage['usage_percent']:.1f}%."
            )

    if "category" in insight_df.columns:
        insights.append(
            f"Recommendation: Prioritize monitoring {top_category} expenses because this category contributes the largest share of spending."
        )

    if "month" in insight_df.columns:
        insights.append(
            f"Recommendation: Use {peak_month} as a reference month when planning future spending controls, since it shows the strongest spending peak."
        )

    insights.append(
        "Conclusion: The dashboard shows that expense monitoring can identify the main spending categories, peak spending periods, budget usage, and payment behavior needed for better financial planning."
    )

    return insights


def generate_placeholder_insights(df):
    """Backward-compatible wrapper for the dashboard import."""
    return generate_insights(df)
