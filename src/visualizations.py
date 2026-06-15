import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


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
