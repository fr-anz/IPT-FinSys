import pandas as pd


def get_basic_summary(df):
    """Return a small summary dictionary for the starter dashboard."""
    summary = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
    }

    if "amount_php" in df.columns:
        amount_values = pd.to_numeric(df["amount_php"], errors="coerce")
        summary["total_transactions"] = amount_values.count()
        summary["average_expense"] = amount_values.mean()

    # TODO Dev 4: Add mean, median, mode, min, max, and standard deviation.
    # TODO Dev 4: Add category totals.
    # TODO Dev 4: Add monthly trends.
    # TODO Dev 4: Add budget summaries.

    return summary
