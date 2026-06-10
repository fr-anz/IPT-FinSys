import matplotlib.pyplot as plt
import pandas as pd


def create_sample_chart(df):
    """Create a simple starter chart if the needed columns are available."""
    if "category" not in df.columns or "amount_php" not in df.columns:
        return None

    chart_df = df.copy()
    chart_df["amount_php"] = pd.to_numeric(chart_df["amount_php"], errors="coerce")
    chart_df = chart_df.dropna(subset=["amount_php"])

    if chart_df.empty:
        return None

    category_totals = chart_df.groupby("category")["amount_php"].sum().sort_values()

    fig, ax = plt.subplots(figsize=(8, 5))
    category_totals.plot(kind="barh", ax=ax)
    ax.set_title("Total Amount by Category")
    ax.set_xlabel("Amount (PHP)")
    ax.set_ylabel("Category")
    fig.tight_layout()

    # TODO Dev 5: Add a full bar graph.
    # TODO Dev 5: Add a line graph.
    # TODO Dev 5: Add a pie chart.
    # TODO Dev 5: Add a histogram or scatter plot.
    # TODO Dev 5: Add a budget vs actual chart.

    return fig
