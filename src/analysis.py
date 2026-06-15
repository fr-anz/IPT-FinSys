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
