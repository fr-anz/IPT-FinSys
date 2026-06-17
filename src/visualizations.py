import os
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(
        Path(__file__).resolve().parents[1]
        / ".matplotlib-cache"
        / f"pid-{os.getpid()}"
    ),
)

import matplotlib

matplotlib.use("Agg")
matplotlib.set_loglevel("error")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

try:
    from src.config import (
        ANALYSIS_OUTPUTS_DIR,
        BUDGET_SUMMARY_PATH,
        CATEGORY_SUMMARY_PATH,
        EXPENSE_GROUP_SUMMARY_PATH,
        FINANCIAL_HEALTH_SUMMARY_PATH,
        MONTHLY_SUMMARY_PATH,
        PROJECT_ROOT,
    )
except ModuleNotFoundError:  # Allows direct execution from inside src/.
    from config import (
        ANALYSIS_OUTPUTS_DIR,
        BUDGET_SUMMARY_PATH,
        CATEGORY_SUMMARY_PATH,
        EXPENSE_GROUP_SUMMARY_PATH,
        FINANCIAL_HEALTH_SUMMARY_PATH,
        MONTHLY_SUMMARY_PATH,
        PROJECT_ROOT,
    )


REPORT_FIGURES_DIR = PROJECT_ROOT / "reports" / "figures"


COLOR_SEQUENCE = [
    "#2f7d6d",
    "#4e7fa1",
    "#7a6aa0",
    "#a65f70",
    "#738b4f",
    "#b2863f",
    "#4f8b8b",
    "#7d8290",
    "#b36b56",
    "#5f8f65",
]

PESO_PREFIX = "PHP "

ANALYSIS_OUTPUT_PATHS = {
    "monthly_summary": MONTHLY_SUMMARY_PATH,
    "category_summary": CATEGORY_SUMMARY_PATH,
    "expense_group_summary": EXPENSE_GROUP_SUMMARY_PATH,
    "budget_variance_summary": BUDGET_SUMMARY_PATH,
    "financial_health_summary": FINANCIAL_HEALTH_SUMMARY_PATH,
}


def _read_csv_if_available(path):
    """Load a CSV file when it exists and contains rows."""
    path = Path(path)
    if not path.exists():
        return pd.DataFrame()

    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def load_analysis_outputs(outputs_dir=ANALYSIS_OUTPUTS_DIR):
    """Load computed analysis output CSVs from data/outputs."""
    outputs_dir = Path(outputs_dir)
    paths = {
        name: outputs_dir / path.name for name, path in ANALYSIS_OUTPUT_PATHS.items()
    }
    return {name: _read_csv_if_available(path) for name, path in paths.items()}


def _clean_columns(df, required_columns):
    """Return a copy containing required columns, or None when unusable."""
    if df is None or df.empty:
        return None

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return None

    return df.copy()


def _clean_monthly_frame(df, value_columns):
    """Return monthly data sorted by year_month with numeric metric columns."""
    chart_df = _clean_columns(df, ["year_month", *value_columns])
    if chart_df is None:
        return None

    chart_df["year_month"] = chart_df["year_month"].astype(str)
    for column in value_columns:
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")
    chart_df = chart_df.dropna(subset=value_columns)

    if chart_df.empty:
        return None

    return chart_df.sort_values("year_month")


def _format_php(value):
    """Return a Philippine Peso label using ASCII-safe PHP notation."""
    if pd.isna(value):
        return f"{PESO_PREFIX}0"
    return f"{PESO_PREFIX}{float(value):,.0f}"


def _apply_plotly_currency_axis(fig, axis="y"):
    """Format Plotly axes with Philippine Peso tick labels."""
    tickformat = ",.0f"
    if axis == "x":
        fig.update_xaxes(tickprefix=PESO_PREFIX, tickformat=tickformat)
    else:
        fig.update_yaxes(tickprefix=PESO_PREFIX, tickformat=tickformat)
    return fig


def _style_analysis_figure(fig, title, height=430):
    """Apply analysis-chart styling with readable spacing and legends."""
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left", font=dict(size=18)),
        height=height,
        margin=dict(l=48, r=28, t=70, b=52),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Aptos, Segoe UI, sans-serif", color="#18201d", size=13),
        hoverlabel=dict(
            bgcolor="#18201d",
            bordercolor="#18201d",
            font=dict(color="#ffffff", family="Aptos, Segoe UI, sans-serif"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.28,
            xanchor="left",
            x=0,
            title_text="",
        ),
    )
    fig.update_xaxes(
        gridcolor="#e7ecea",
        linecolor="#d9dfdc",
        tickfont=dict(color="#68716c"),
        title_font=dict(color="#68716c"),
        zerolinecolor="#d9dfdc",
    )
    fig.update_yaxes(
        gridcolor="#e7ecea",
        linecolor="#d9dfdc",
        tickfont=dict(color="#68716c"),
        title_font=dict(color="#68716c"),
        zerolinecolor="#d9dfdc",
    )
    return fig


def create_monthly_income_expenses_line(monthly_summary):
    """Create a Plotly monthly income vs expenses line chart."""
    chart_df = _clean_monthly_frame(
        monthly_summary, ["total_income", "total_expenses"]
    )
    if chart_df is None:
        return None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            name="Income",
            x=chart_df["year_month"],
            y=chart_df["total_income"],
            mode="lines+markers",
            line=dict(color="#2f7d6d", width=3),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b><br>Income: PHP %{y:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            name="Expenses",
            x=chart_df["year_month"],
            y=chart_df["total_expenses"],
            mode="lines+markers",
            line=dict(color="#a65f70", width=3),
            marker=dict(size=8),
            hovertemplate="<b>%{x}</b><br>Expenses: PHP %{y:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(xaxis_title="Month", yaxis_title="Amount (PHP)")
    _apply_plotly_currency_axis(fig)
    return _style_analysis_figure(fig, "Monthly Income vs Expenses")


def create_expenses_by_category_bar(category_summary, top_n=None):
    """Create a Plotly bar chart of expenses by category."""
    chart_df = _clean_columns(category_summary, ["category", "total_spent"])
    if chart_df is None:
        return None

    chart_df["total_spent"] = pd.to_numeric(chart_df["total_spent"], errors="coerce")
    chart_df = chart_df.dropna(subset=["total_spent"]).sort_values("total_spent")
    if top_n:
        chart_df = chart_df.tail(top_n)
    if chart_df.empty:
        return None

    fig = px.bar(
        chart_df,
        x="total_spent",
        y="category",
        orientation="h",
        color="category",
        color_discrete_sequence=COLOR_SEQUENCE,
        labels={"total_spent": "Total Spent (PHP)", "category": "Category"},
        text="total_spent",
    )
    fig.update_traces(
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Spent: PHP %{x:,.2f}<extra></extra>",
        marker_line_width=0,
        texttemplate="PHP %{text:,.0f}",
        textposition="outside",
    )
    fig.update_layout(showlegend=False)
    _apply_plotly_currency_axis(fig, axis="x")
    styled = _style_analysis_figure(fig, "Expenses by Category", height=460)
    max_amount = float(chart_df["total_spent"].max() or 0)
    if max_amount > 0:
        styled.update_xaxes(range=[0, max_amount * 1.18])
    styled.update_layout(margin=dict(l=60, r=58, t=70, b=52))
    return styled


def create_expense_group_distribution_pie(expense_group_summary):
    """Create a Plotly pie chart showing needs/wants spending distribution."""
    chart_df = _clean_columns(expense_group_summary, ["expense_group", "total_spent"])
    if chart_df is None:
        return None

    chart_df["total_spent"] = pd.to_numeric(chart_df["total_spent"], errors="coerce")
    chart_df = chart_df.dropna(subset=["total_spent"])
    chart_df = chart_df[chart_df["total_spent"] > 0]
    if chart_df.empty:
        return None

    fig = px.pie(
        chart_df,
        values="total_spent",
        names="expense_group",
        color_discrete_sequence=COLOR_SEQUENCE,
        hole=0.42,
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Spent: PHP %{value:,.2f}<br>%{percent}<extra></extra>",
        marker=dict(line=dict(color="#ffffff", width=2)),
        textinfo="label+percent",
    )
    return _style_analysis_figure(fig, "Expense Group Distribution", height=430)


def create_monthly_savings_rate_line(monthly_summary):
    """Create a Plotly monthly savings rate line chart."""
    chart_df = _clean_monthly_frame(monthly_summary, ["savings_rate"])
    if chart_df is None:
        return None

    fig = px.line(
        chart_df,
        x="year_month",
        y="savings_rate",
        markers=True,
        labels={"year_month": "Month", "savings_rate": "Savings Rate (%)"},
    )
    fig.update_traces(
        line=dict(color="#4e7fa1", width=3),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Savings rate: %{y:.2f}%<extra></extra>",
    )
    fig.add_hline(
        y=15,
        line_dash="dash",
        line_color="#738b4f",
        annotation_text="15% target",
        annotation_position="top left",
    )
    return _style_analysis_figure(fig, "Monthly Savings Rate")


def create_budget_variance_by_category_bar(budget_variance_summary):
    """Create a Plotly bar chart of category budget variance."""
    chart_df = _clean_columns(budget_variance_summary, ["category", "budget_variance"])
    if chart_df is None:
        return None

    chart_df["budget_variance"] = pd.to_numeric(
        chart_df["budget_variance"], errors="coerce"
    )
    chart_df = chart_df.dropna(subset=["budget_variance"])
    if chart_df.empty:
        return None

    chart_df = chart_df.sort_values("budget_variance")
    colors = np.where(chart_df["budget_variance"] > 0, "#a65f70", "#2f7d6d")

    fig = go.Figure(
        go.Bar(
            x=chart_df["budget_variance"],
            y=chart_df["category"],
            orientation="h",
            marker_color=colors,
            text=[_format_php(value) for value in chart_df["budget_variance"]],
            textposition="outside",
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>Variance: PHP %{x:,.2f}<extra></extra>",
        )
    )
    fig.add_vline(x=0, line_width=1, line_color="#68716c")
    fig.update_layout(
        xaxis_title="Budget Variance (PHP)",
        yaxis_title="Category",
        showlegend=False,
    )
    _apply_plotly_currency_axis(fig, axis="x")
    return _style_analysis_figure(fig, "Budget Variance by Category", height=460)


def create_financial_health_score_line(financial_health_summary):
    """Create a Plotly financial health score trend chart."""
    chart_df = _clean_monthly_frame(financial_health_summary, ["financial_health_score"])
    if chart_df is None:
        return None

    fig = px.line(
        chart_df,
        x="year_month",
        y="financial_health_score",
        markers=True,
        labels={"year_month": "Month", "financial_health_score": "Score (0-100)"},
    )
    fig.update_traces(
        line=dict(color="#7a6aa0", width=3),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Health score: %{y:.2f}<extra></extra>",
    )
    fig.update_yaxes(range=[0, 100])
    return _style_analysis_figure(fig, "Financial Health Score Over Time")


def create_analysis_visualization_charts(analysis_outputs=None, df=None):
    """Return reusable Plotly charts built from saved analysis outputs."""
    data = analysis_outputs or load_analysis_outputs()
    return {
        "Monthly income vs expenses": create_monthly_income_expenses_line(
            data.get("monthly_summary")
        ),
        "Expenses by category": create_expenses_by_category_bar(
            data.get("category_summary")
        ),
        "Expense group distribution": create_expense_group_distribution_pie(
            data.get("expense_group_summary")
        ),
        "Monthly savings rate": create_monthly_savings_rate_line(
            data.get("monthly_summary")
        ),
        "Budget variance by category": create_budget_variance_by_category_bar(
            data.get("budget_variance_summary")
        ),
        "Financial health score over time": create_financial_health_score_line(
            data.get("financial_health_summary")
        ),
        "Expense amount distribution": create_histogram(df) if df is not None else None,
        "Payment method distribution": create_payment_method_pie(df) if df is not None else None,
    }


def _style_matplotlib_axes(ax, title, xlabel=None, ylabel=None):
    """Apply readable Matplotlib styling for exported documentation charts."""
    ax.set_title(title, loc="left", fontsize=13, pad=14, weight="bold")
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", color="#e7ecea", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#d9dfdc")
    ax.spines["bottom"].set_color("#d9dfdc")
    ax.tick_params(colors="#68716c")
    return ax


def _save_matplotlib_figure(fig, path):
    """Persist a Matplotlib figure and close it after saving."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return path


def export_analysis_charts_png(
    analysis_outputs=None,
    figures_dir=REPORT_FIGURES_DIR,
):
    """Optionally export analysis charts as PNG files under reports/figures."""
    data = analysis_outputs or load_analysis_outputs()
    figures_dir = Path(figures_dir)
    saved_paths = {}

    monthly = _clean_monthly_frame(
        data.get("monthly_summary"), ["total_income", "total_expenses", "savings_rate"]
    )
    if monthly is not None:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        ax.plot(
            monthly["year_month"],
            monthly["total_income"],
            marker="o",
            label="Income",
            color="#2f7d6d",
        )
        ax.plot(
            monthly["year_month"],
            monthly["total_expenses"],
            marker="o",
            label="Expenses",
            color="#a65f70",
        )
        _style_matplotlib_axes(
            ax, "Monthly Income vs Expenses", "Month", "Amount (PHP)"
        )
        ax.yaxis.set_major_formatter(lambda value, _: _format_php(value))
        ax.legend(frameon=False)
        ax.tick_params(axis="x", rotation=35)
        saved_paths["monthly_income_vs_expenses"] = _save_matplotlib_figure(
            fig, figures_dir / "monthly_income_vs_expenses.png"
        )

        fig, ax = plt.subplots(figsize=(9, 4.8))
        ax.plot(
            monthly["year_month"],
            monthly["savings_rate"],
            marker="o",
            color="#4e7fa1",
            label="Savings rate",
        )
        ax.axhline(
            15,
            linestyle="--",
            color="#738b4f",
            linewidth=1.2,
            label="15% target",
        )
        _style_matplotlib_axes(ax, "Monthly Savings Rate", "Month", "Savings Rate (%)")
        ax.legend(frameon=False)
        ax.tick_params(axis="x", rotation=35)
        saved_paths["monthly_savings_rate"] = _save_matplotlib_figure(
            fig, figures_dir / "monthly_savings_rate.png"
        )

    categories = _clean_columns(
        data.get("category_summary"), ["category", "total_spent"]
    )
    if categories is not None:
        categories["total_spent"] = pd.to_numeric(
            categories["total_spent"], errors="coerce"
        )
        categories = categories.dropna(subset=["total_spent"]).sort_values("total_spent")
        if not categories.empty:
            fig, ax = plt.subplots(figsize=(9, 5.2))
            ax.barh(categories["category"], categories["total_spent"], color="#2f7d6d")
            _style_matplotlib_axes(
                ax, "Expenses by Category", "Total Spent (PHP)", "Category"
            )
            ax.xaxis.set_major_formatter(lambda value, _: _format_php(value))
            saved_paths["expenses_by_category"] = _save_matplotlib_figure(
                fig, figures_dir / "expenses_by_category.png"
            )

    groups = _clean_columns(
        data.get("expense_group_summary"), ["expense_group", "total_spent"]
    )
    if groups is not None:
        groups["total_spent"] = pd.to_numeric(groups["total_spent"], errors="coerce")
        groups = groups.dropna(subset=["total_spent"])
        groups = groups[groups["total_spent"] > 0]
        if not groups.empty:
            fig, ax = plt.subplots(figsize=(6.5, 5.2))
            ax.pie(
                groups["total_spent"],
                labels=groups["expense_group"],
                autopct="%1.1f%%",
                colors=COLOR_SEQUENCE[: len(groups)],
                startangle=90,
                wedgeprops=dict(edgecolor="#ffffff", linewidth=1),
            )
            ax.set_title(
                "Expense Group Distribution",
                loc="left",
                fontsize=13,
                pad=14,
                weight="bold",
            )
            saved_paths["expense_group_distribution"] = _save_matplotlib_figure(
                fig, figures_dir / "expense_group_distribution.png"
            )

    variance = _clean_columns(
        data.get("budget_variance_summary"), ["category", "budget_variance"]
    )
    if variance is not None:
        variance["budget_variance"] = pd.to_numeric(
            variance["budget_variance"], errors="coerce"
        )
        variance = variance.dropna(subset=["budget_variance"]).sort_values(
            "budget_variance"
        )
        if not variance.empty:
            fig, ax = plt.subplots(figsize=(9, 5.2))
            colors = np.where(variance["budget_variance"] > 0, "#a65f70", "#2f7d6d")
            ax.barh(variance["category"], variance["budget_variance"], color=colors)
            ax.axvline(0, color="#68716c", linewidth=1)
            _style_matplotlib_axes(
                ax, "Budget Variance by Category", "Budget Variance (PHP)", "Category"
            )
            ax.xaxis.set_major_formatter(lambda value, _: _format_php(value))
            saved_paths["budget_variance_by_category"] = _save_matplotlib_figure(
                fig, figures_dir / "budget_variance_by_category.png"
            )

    health = _clean_monthly_frame(
        data.get("financial_health_summary"), ["financial_health_score"]
    )
    if health is not None:
        fig, ax = plt.subplots(figsize=(9, 4.8))
        ax.plot(
            health["year_month"],
            health["financial_health_score"],
            marker="o",
            color="#7a6aa0",
            label="Financial health score",
        )
        ax.set_ylim(0, 100)
        _style_matplotlib_axes(
            ax, "Financial Health Score Over Time", "Month", "Score (0-100)"
        )
        ax.legend(frameon=False)
        ax.tick_params(axis="x", rotation=35)
        saved_paths["financial_health_score_over_time"] = _save_matplotlib_figure(
            fig, figures_dir / "financial_health_score_over_time.png"
        )

    return saved_paths


def _prepare_amount_data(df, required_columns):
    """Return a chart-ready copy when the required columns exist."""
    missing_columns = [
        col for col in required_columns + ["amount_php"] if col not in df.columns
    ]
    if missing_columns:
        return None

    chart_df = df.copy()
    chart_df["amount_php"] = pd.to_numeric(chart_df["amount_php"], errors="coerce")
    chart_df = chart_df.dropna(subset=["amount_php"])

    if chart_df.empty:
        return None

    return chart_df


def _expense_only(df):
    """Return rows that represent actual expenses, excluding refunds."""
    return df[df["amount_php"] > 0].copy()


def _ensure_month_column(df):
    """Return a copy with a string month column when possible."""
    chart_df = df.copy()
    if "month" in chart_df.columns:
        chart_df["month"] = chart_df["month"].astype(str)
    elif "date" in chart_df.columns:
        chart_df["month"] = pd.to_datetime(
            chart_df["date"], errors="coerce"
        ).dt.to_period("M").astype(str)
    else:
        return None

    chart_df = chart_df[chart_df["month"].astype(str) != "NaT"].dropna(
        subset=["month"]
    )
    return chart_df if not chart_df.empty else None


def _category_month_budgets(df):
    """Return deduplicated category-month budgets plus positive expenses."""
    budget_df = _prepare_amount_data(df, ["category", "budget_limit_php"])
    if budget_df is None:
        return None

    budget_df["budget_limit_php"] = pd.to_numeric(
        budget_df["budget_limit_php"], errors="coerce"
    ).fillna(0)
    budget_df = _ensure_month_column(budget_df)
    if budget_df is None:
        return None

    expenses = (
        _expense_only(budget_df)
        .groupby("category", observed=True)["amount_php"]
        .sum()
    )
    budgets = (
        budget_df.groupby(["category", "month"], observed=True)["budget_limit_php"]
        .max()
        .groupby("category", observed=True)
        .sum()
    )
    return (
        pd.DataFrame({"actual_spending": expenses, "budget_limit": budgets})
        .fillna(0)
        .reset_index()
    )


def _style_figure(fig, height=390):
    """Apply a consistent visual style to Plotly figures."""
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=24, b=18),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#ffffff",
        font=dict(family="Aptos, Segoe UI, sans-serif", color="#18201d", size=13),
        hoverlabel=dict(
            bgcolor="#18201d",
            bordercolor="#18201d",
            font=dict(color="#ffffff", family="Aptos, Segoe UI, sans-serif"),
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.22,
            xanchor="left",
            x=0,
            title_text="",
        ),
    )
    fig.update_xaxes(
        gridcolor="#e7ecea",
        linecolor="#d9dfdc",
        tickfont=dict(color="#68716c"),
        title_font=dict(color="#68716c"),
        zerolinecolor="#d9dfdc",
    )
    fig.update_yaxes(
        gridcolor="#e7ecea",
        linecolor="#d9dfdc",
        tickfont=dict(color="#68716c"),
        title_font=dict(color="#68716c"),
        zerolinecolor="#d9dfdc",
    )
    return fig


def create_bar_graph(df):
    """Create a bar graph of positive expense totals by category."""
    chart_df = _prepare_amount_data(df, ["category"])
    if chart_df is None:
        return None
    chart_df = _expense_only(chart_df)
    if chart_df.empty:
        return None

    category_totals = (
        chart_df.groupby("category", observed=True)["amount_php"]
        .sum()
        .reset_index()
        .sort_values("amount_php")
    )

    fig = px.bar(
        category_totals,
        x="amount_php",
        y="category",
        orientation="h",
        color="category",
        color_discrete_sequence=COLOR_SEQUENCE,
        labels={"amount_php": "Expenses (PHP)", "category": "Category"},
        text="amount_php",
    )
    fig.update_traces(
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>PHP %{x:,.2f}<extra></extra>",
        marker_line_width=0,
        texttemplate="PHP %{text:,.0f}",
        textposition="outside",
    )
    fig.update_layout(showlegend=False)
    styled = _style_figure(fig)
    max_amount = float(category_totals["amount_php"].max() or 0)
    if max_amount > 0:
        styled.update_xaxes(range=[0, max_amount * 1.18])
    styled.update_layout(margin=dict(l=18, r=48, t=24, b=18))
    return styled


def create_line_graph(df):
    """Create a line graph of monthly positive expense trends."""
    chart_df = _prepare_amount_data(df, [])
    if chart_df is None:
        return None

    chart_df = _ensure_month_column(chart_df)
    if chart_df is None:
        return None
    chart_df = _expense_only(chart_df)
    if chart_df.empty:
        return None

    monthly_totals = (
        chart_df.groupby("month")["amount_php"].sum().reset_index().sort_values("month")
    )

    fig = px.line(
        monthly_totals,
        x="month",
        y="amount_php",
        markers=True,
        labels={"month": "Month", "amount_php": "Expenses (PHP)"},
    )
    fig.update_traces(
        line=dict(color="#2f7d6d", width=3),
        marker=dict(size=8, color="#ffffff", line=dict(color="#2f7d6d", width=2)),
        hovertemplate="<b>%{x}</b><br>PHP %{y:,.2f}<extra></extra>",
    )
    return _style_figure(fig)


def create_pie_chart(df):
    """Create a pie chart showing spending share by category."""
    chart_df = _prepare_amount_data(df, ["category"])
    if chart_df is None:
        return None

    chart_df = chart_df[chart_df["amount_php"] > 0]
    if chart_df.empty:
        return None

    category_totals = (
        chart_df.groupby("category", observed=True)["amount_php"]
        .sum()
        .reset_index()
        .sort_values("amount_php", ascending=False)
    )

    fig = px.pie(
        category_totals,
        values="amount_php",
        names="category",
        color_discrete_sequence=COLOR_SEQUENCE,
        hole=0.48,
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>PHP %{value:,.2f}<br>%{percent}<extra></extra>",
        marker=dict(line=dict(color="#ffffff", width=2)),
        textinfo="percent",
        textfont=dict(color="#ffffff", size=12),
    )
    fig.add_annotation(
        text="Share",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(color="#68716c", size=14),
    )
    return _style_figure(fig, height=420)


def create_histogram(df):
    """Create a histogram of transaction amounts."""
    chart_df = _prepare_amount_data(df, [])
    if chart_df is None:
        return None

    fig = px.histogram(
        chart_df,
        x="amount_php",
        nbins=24,
        labels={"amount_php": "Amount (PHP)", "count": "Transactions"},
        color_discrete_sequence=["#2f7d6d"],
    )
    fig.update_traces(
        hovertemplate="PHP %{x:,.2f}<br>%{y:,} transactions<extra></extra>",
        marker_line_color="#ffffff",
        marker_line_width=1,
    )
    return _style_figure(fig)


def create_budget_vs_actual_chart(df):
    """Create a category chart comparing monthly budgets with actual expenses."""
    budget_totals = _category_month_budgets(df)
    if budget_totals is None or budget_totals.empty:
        return None
    budget_totals = budget_totals.sort_values("actual_spending")

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Budget limit",
            x=budget_totals["budget_limit"],
            y=budget_totals["category"],
            orientation="h",
            marker_color="#cfd8d4",
            hovertemplate="<b>%{y}</b><br>Budget: PHP %{x:,.2f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="Actual spending",
            x=budget_totals["actual_spending"],
            y=budget_totals["category"],
            orientation="h",
            marker_color="#2f7d6d",
            hovertemplate="<b>%{y}</b><br>Expenses: PHP %{x:,.2f}<extra></extra>",
        )
    )
    fig.update_layout(
        barmode="group",
        xaxis_title="Amount (PHP)",
        yaxis_title="Category",
    )
    return _style_figure(fig, height=420)


def create_budget_gauge(budget_usage_percent):
    """Create a donut gauge showing budget usage as a percentage."""
    if budget_usage_percent is None:
        return None

    usage = max(0.0, float(budget_usage_percent))
    display_usage = min(usage, 100.0)
    remaining = max(0.0, 100.0 - display_usage)
    arc_color = "#9d5d28" if usage > 100 else "#2f7d6d"

    fig = go.Figure(
        go.Pie(
            values=[display_usage, remaining],
            hole=0.72,
            sort=False,
            direction="clockwise",
            rotation=0,
            marker=dict(colors=[arc_color, "#e7ecea"], line=dict(color="#ffffff", width=1)),
            textinfo="none",
            hoverinfo="skip",
        )
    )
    fig.add_annotation(
        text=f"<b>{usage:.1f}%</b>",
        x=0.5,
        y=0.52,
        showarrow=False,
        font=dict(color="#18201d", size=26),
    )
    fig.add_annotation(
        text="of budget used",
        x=0.5,
        y=0.34,
        showarrow=False,
        font=dict(color="#68716c", size=12),
    )
    fig.update_layout(
        height=210,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Aptos, Segoe UI, sans-serif"),
    )
    return fig


def create_mini_monthly_line(df):
    """Create a compact monthly expense line for embedding in a card."""
    chart_df = _prepare_amount_data(df, [])
    if chart_df is None:
        return None

    chart_df = _ensure_month_column(chart_df)
    if chart_df is None:
        return None
    chart_df = _expense_only(chart_df)
    if chart_df.empty:
        return None

    monthly = (
        chart_df.groupby("month")["amount_php"].sum().reset_index().sort_values("month")
    )

    fig = px.area(monthly, x="month", y="amount_php")
    fig.update_traces(
        line=dict(color="#2f7d6d", width=2.5),
        fillcolor="rgba(47, 125, 109, 0.12)",
        hovertemplate="<b>%{x}</b><br>PHP %{y:,.2f}<extra></extra>",
    )
    fig.update_layout(
        height=190,
        margin=dict(l=6, r=6, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Aptos, Segoe UI, sans-serif", color="#68716c", size=11),
    )
    fig.update_xaxes(showgrid=False, title_text="", tickfont=dict(size=10))
    fig.update_yaxes(showgrid=False, visible=False, title_text="")
    return fig


def create_top_categories_bar(df, top_n=5):
    """Create a compact horizontal bar of the top positive expense categories."""
    chart_df = _prepare_amount_data(df, ["category"])
    if chart_df is None:
        return None
    chart_df = _expense_only(chart_df)
    if chart_df.empty:
        return None

    totals = (
        chart_df.groupby("category", observed=True)["amount_php"]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .sort_values()
        .reset_index()
    )
    if totals.empty:
        return None

    fig = px.bar(
        totals,
        x="amount_php",
        y="category",
        orientation="h",
        color_discrete_sequence=["#2f7d6d"],
        text="amount_php",
    )
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>PHP %{x:,.2f}<extra></extra>",
        marker_line_width=0,
        texttemplate="PHP %{text:,.0f}",
        textposition="outside",
        cliponaxis=False,
    )
    max_amount = float(totals["amount_php"].max() or 0)
    fig.update_layout(
        height=200,
        margin=dict(l=6, r=48, t=6, b=6),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family="Aptos, Segoe UI, sans-serif", color="#68716c", size=11),
    )
    if max_amount > 0:
        fig.update_xaxes(visible=False, range=[0, max_amount * 1.22])
    else:
        fig.update_xaxes(visible=False, autorange=True)
    fig.update_yaxes(showgrid=False, title_text="", tickfont=dict(color="#18201d", size=12))
    return fig


def create_payment_method_pie(df):
    """Create a pie chart showing expense distribution by payment method."""
    chart_df = _prepare_amount_data(df, ["payment_method"])
    if chart_df is None:
        return None

    chart_df = _expense_only(chart_df)
    if chart_df.empty:
        return None

    payment_totals = (
        chart_df.groupby("payment_method", observed=True)["amount_php"]
        .sum()
        .reset_index()
        .sort_values("amount_php", ascending=False)
    )
    payment_totals = payment_totals[payment_totals["amount_php"] > 0]
    if payment_totals.empty:
        return None

    fig = px.pie(
        payment_totals,
        values="amount_php",
        names="payment_method",
        color_discrete_sequence=COLOR_SEQUENCE,
        hole=0.48,
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>PHP %{value:,.2f}<br>%{percent}<extra></extra>",
        marker=dict(line=dict(color="#ffffff", width=2)),
        textinfo="percent+label",
        textfont=dict(size=12),
    )
    fig.add_annotation(
        text="Payment",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(color="#68716c", size=13),
    )
    return _style_figure(fig, height=420)


def create_visualization_charts(df):
    """Return all available dashboard charts."""
    return {
        "Category expenses": create_bar_graph(df),
        "Monthly expenses": create_line_graph(df),
        "Category share": create_pie_chart(df),
        "Amount distribution": create_histogram(df),
        "Budget vs expenses": create_budget_vs_actual_chart(df),
    }


def create_sample_chart(df):
    """Create the default chart used by the dashboard."""
    return create_bar_graph(df)