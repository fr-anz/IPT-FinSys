import pandas as pd

from src.analysis import get_basic_summary


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
    """Generate analytical findings from the filtered dashboard data."""
    insight_df = _prepare_insight_data(df)
    if insight_df is None:
        return ["No insight can be generated because the selected data is empty."]

    insights = []
    summary = get_basic_summary(insight_df)
    total_expenses = summary.get("gross_expense_total", 0)
    refund_total = summary.get("refund_total", 0)
    net_spending = summary.get("net_spending", 0)

    budget_summary = summary.get("budget_summary", {})
    budget_usage = budget_summary.get("budget_usage_percent", 0)
    remaining_budget = budget_summary.get("remaining_budget")
    if budget_summary:
        if budget_usage > 100:
            insights.append(
                f"Budget variance: Expenses exceed the monthly category budget by {_format_php(abs(remaining_budget))}. Budget utilization is {budget_usage:.1f}%, indicating that actual spending is materially above the planned allocation."
            )
        else:
            insights.append(
                f"Budget variance: Expenses used {budget_usage:.1f}% of the monthly category budget, leaving {_format_php(remaining_budget)} unspent. The selected period remains within the planned allocation."
            )

    budget_by_category = summary.get("budget_by_category", {})
    if budget_by_category:
        budget_df = pd.DataFrame.from_dict(budget_by_category, orient="index")
        budget_df = budget_df[budget_df["total_budget"] > 0]
        if not budget_df.empty:
            highest_usage = budget_df.sort_values(
                "usage_percent", ascending=False
            ).iloc[0]
            gap = highest_usage["total_spent"] - highest_usage["total_budget"]
            position = (
                f"over budget by {_format_php(gap)}"
                if gap > 0
                else f"within budget by {_format_php(abs(gap))}"
            )
            insights.append(
                f"Budget exposure: {highest_usage.name} has the highest category-level utilization at {highest_usage['usage_percent']:.1f}% and is {position}. This category should be reviewed first because it contributes the strongest budget pressure."
            )

    category_totals = summary.get("category_totals", {})
    if category_totals and total_expenses:
        top_category, top_category_total = next(iter(category_totals.items()))
        category_share = (top_category_total / total_expenses) * 100
        insights.append(
            f"Category concentration: {top_category} is the largest expense category at {_format_php(top_category_total)}, representing {category_share:.1f}% of total expenses. Monitoring this category will have the highest impact on overall spending control."
        )

    if refund_total:
        refund_share = (refund_total / total_expenses) * 100 if total_expenses else 0
        insights.append(
            f"Refund adjustment: Refunds reduced net spending by {_format_php(refund_total)}, equivalent to {refund_share:.1f}% of expenses. Reporting both expenses before refunds and net spending keeps the refund effect visible."
        )

    monthly_trends = summary.get("monthly_trends", {})
    if monthly_trends:
        monthly_df = pd.DataFrame.from_dict(monthly_trends, orient="index")
        expense_series = monthly_df["gross_expense_total"].sort_index()
        peak_month = expense_series.idxmax()
        peak_month_total = expense_series.loc[peak_month]
        insights.append(
            f"Peak period: Expenses reached their highest monthly value in {peak_month} at {_format_php(peak_month_total)}. This period should be used as the reference point for investigating unusual activity or seasonal spending."
        )

        month_changes = expense_series.diff().dropna()
        if not month_changes.empty:
            biggest_change = month_changes.loc[month_changes.abs().idxmax()]
            change_month = month_changes.abs().idxmax()
            direction = "increased" if biggest_change >= 0 else "decreased"
            insights.append(
                f"Monthly volatility: The largest month-to-month movement occurred in {change_month}, when expenses {direction} by {_format_php(abs(biggest_change))}. This indicates the strongest short-term shift in spending behavior."
            )

    if "necessity_type" in insight_df.columns:
        expense_mask = insight_df["amount_php"] > 0
        if "transaction_type" in insight_df.columns:
            expense_mask &= (
                insight_df["transaction_type"].astype(str).str.strip().str.lower()
                == "expense"
            )
        elif "category" in insight_df.columns:
            expense_mask &= (
                insight_df["category"].astype(str).str.strip().str.lower()
                != "income"
            )
        necessity_totals = (
            insight_df[expense_mask]
            .groupby("necessity_type", observed=True)["amount_php"]
            .sum()
            .sort_values(ascending=False)
        )
        if not necessity_totals.empty:
            top_necessity = necessity_totals.index[0]
            priority_share = (
                necessity_totals.iloc[0] / total_expenses * 100
                if total_expenses
                else 0
            )
            insights.append(
                f"Priority mix: {top_necessity} transactions account for the largest priority-group expense at {_format_php(necessity_totals.iloc[0])}, or {priority_share:.1f}% of expenses. This helps distinguish essential spending pressure from discretionary behavior."
            )

    insights.append(
        f"Analytical conclusion: The dashboard separates expenses, refunds, and net spending. Under this view, current net spending is {_format_php(net_spending)} after refunds."
    )

    return insights


def generate_placeholder_insights(df):
    """Backward-compatible wrapper for the dashboard import."""
    return generate_insights(df)
