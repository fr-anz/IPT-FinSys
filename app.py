from html import escape
import re

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

from src.analysis import (
    get_basic_summary,
    get_preprocessed_financial_analysis,
    save_analysis_summaries,
)
from src.config import BASE_DATASET_NAME
from src.data_cleaning import clean_dataset
from src.data_loader import load_raw_dataset, save_cleaned_dataset
from src.insights import generate_insights
from src.summary_exports import export_summary_csvs
from src.visualizations import (
    create_analysis_visualization_charts,
    create_budget_vs_actual_chart,
    create_budget_gauge,
    create_budget_variance_by_category_bar,
    create_expenses_by_category_bar,
    create_monthly_income_expenses_line,
    create_mini_monthly_line,
    create_top_categories_bar,
    create_visualization_charts,
    load_analysis_outputs,
)


st.set_page_config(
    page_title="Financial Expense Monitoring Dashboard",
    layout="wide",
    initial_sidebar_state="auto",
)


def inject_styles():
    """Apply the dashboard visual system."""
    st.markdown(
        """
        <style>
        :root {
            --page: #f7f8fb;
            --surface: #ffffff;
            --surface-strong: #f1f4f7;
            --ink: #101633;
            --muted: #838aa3;
            --line: #e8ecf3;
            --accent: #2f7d6d;
            --accent-dark: #205a50;
            --warning: #9d5d28;
            --risk: #c25362;
            --blue: #3387d5;
            --amber: #d9972b;
            --shadow: 0 24px 60px -34px rgba(29, 42, 74, 0.32);
        }

        html, body, [class*="css"] {
            font-family: "Outfit", "Aptos", "Segoe UI", system-ui, sans-serif;
            color: var(--ink);
        }

        .stApp {
            background:
                radial-gradient(circle at 80% 0%, rgba(47, 125, 109, 0.06), transparent 28rem),
                var(--page);
        }

        .block-container {
            max-width: 1480px;
            padding-top: 1.65rem;
            padding-bottom: 3.5rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 0;
            box-shadow: 24px 0 60px -48px rgba(29, 42, 74, 0.38);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding: 1.45rem 1.25rem 2rem;
        }

        /* Hide Streamlit dev chrome (Deploy + menu) but keep the toolbar so the
           sidebar-expand control still works on mobile */
        [data-testid="stAppDeployButton"] { display: none !important; }
        [data-testid="stMainMenu"] { display: none !important; }
        [data-testid="stStatusWidget"] { display: none; }
        [data-testid="stDecoration"] { display: none; }
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; height: 0; }
        header[data-testid="stHeader"] {
            background: transparent;
            pointer-events: none;
        }
        header[data-testid="stHeader"] * { pointer-events: auto; }

        .brand-text { display: flex; flex-direction: column; line-height: 1.08; }
        .brand-name {
            color: var(--ink);
            font-size: 1.34rem;
            font-weight: 820;
            letter-spacing: -0.03em;
        }
        .brand-sub { color: var(--muted); font-size: 0.74rem; font-weight: 640; margin-top: 0.25rem; }

        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--ink);
            letter-spacing: 0;
        }

        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid rgba(217, 223, 220, 0.95);
            border-radius: 8px;
            padding: 1rem 1rem 0.85rem;
            box-shadow: var(--shadow);
        }

        div[data-testid="stMetricLabel"] p {
            color: var(--muted);
            font-size: 0.78rem;
            font-weight: 650;
        }

        div[data-testid="stMetricValue"] {
            font-variant-numeric: tabular-nums;
        }

        .section-heading {
            align-items: end;
            border-top: 1px solid rgba(217, 223, 220, 0.95);
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin: 1.5rem 0 0.75rem;
            padding-top: 1.1rem;
        }

        .section-heading h2 {
            color: var(--ink);
            font-size: 1.25rem;
            font-weight: 720;
            letter-spacing: 0;
            line-height: 1.1;
            margin: 0;
        }

        .section-heading span {
            color: var(--muted);
            font-size: 0.88rem;
            line-height: 1.45;
            max-width: 52ch;
        }

        .insight-item {
            background: rgba(255, 253, 248, 0.72);
            border-left: 3px solid var(--accent);
            border-radius: 8px;
            color: var(--ink);
            line-height: 1.55;
            margin-bottom: 0.65rem;
            padding: 0.85rem 1rem;
        }

        .stButton > button {
            background: var(--accent);
            border: 1px solid var(--accent);
            border-radius: 8px;
            color: #ffffff;
            font-weight: 700;
            transition: transform 180ms ease, background 180ms ease;
        }

        .stButton > button:hover {
            background: var(--accent-dark);
            border-color: var(--accent-dark);
            color: #ffffff;
            transform: translateY(-1px);
        }

        .stButton > button:active {
            transform: scale(0.985);
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid rgba(217, 223, 220, 0.95);
            border-radius: 8px;
            overflow: hidden;
        }

        /* Inner tab bar (Analysis / Data) styled as a segmented control */
        div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
            gap: 0.35rem;
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 10px;
            padding: 0.35rem;
            box-shadow: var(--shadow);
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            height: auto;
            padding: 0.5rem 1rem;
            border-radius: 7px;
            color: var(--muted);
            font-weight: 680;
            font-size: 0.9rem;
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
            background: var(--surface-strong);
            color: var(--ink);
        }

        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
            background: var(--accent);
            color: #ffffff;
        }

        div[data-testid="stTabs"] div[data-baseweb="tab-highlight"],
        div[data-testid="stTabs"] div[data-baseweb="tab-border"] {
            display: none;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 0.65rem;
            margin-top: 0.4rem;
        }

        .stat-tile {
            background: var(--surface);
            border: 1px solid rgba(217, 223, 220, 0.95);
            border-radius: 8px;
            box-shadow: var(--shadow);
            padding: 0.85rem 0.9rem;
        }

        .stat-tile .stat-label {
            color: var(--muted);
            display: block;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }

        .stat-tile .stat-value {
            color: var(--ink);
            display: block;
            font-size: 1.12rem;
            font-variant-numeric: tabular-nums;
            font-weight: 740;
            line-height: 1.1;
            overflow-wrap: anywhere;
        }

        @media (max-width: 980px) {
            .stat-grid { grid-template-columns: repeat(3, 1fr); }
        }

        /* ---- Page title bar (replaces the marketing hero) ---- */
        .page-title-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.35rem;
        }

        .page-title-bar .pt-left { display: flex; flex-direction: column; gap: 0.2rem; }
        .page-title-bar .pt-title {
            color: var(--ink);
            font-size: clamp(1.85rem, 2.1vw, 2.45rem);
            font-weight: 820;
            letter-spacing: -0.045em;
            line-height: 1.1;
            margin: 0;
        }
        .page-title-bar .pt-meta {
            color: var(--muted);
            font-size: 0.88rem;
            font-weight: 590;
            margin-top: 0.35rem;
        }
        /* ---- Sidebar brand ---- */
        .sb-brand { display: flex; align-items: center; gap: 0.65rem; padding: 0 0.25rem 0.5rem; }

        /* Bordered containers act as bento cards */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface);
            border: 1px solid rgba(232, 236, 243, 0.82);
            border-radius: 24px;
            box-shadow: var(--shadow);
        }
        .bento-title { color: var(--ink); font-size: 1.05rem; font-weight: 780; letter-spacing: -0.02em; }
        .bento-sub { color: var(--muted); font-size: 0.82rem; margin: 0.2rem 0 0.45rem; }

        .summary-panel {
            background: var(--surface);
            border: 1px solid rgba(232, 236, 243, 0.88);
            border-radius: 26px;
            box-shadow: var(--shadow);
            min-height: 18rem;
            padding: 1.55rem;
        }
        .summary-head {
            align-items: start;
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.35rem;
        }
        .summary-title { color: var(--ink); display: block; font-size: 1.12rem; font-weight: 800; letter-spacing: -0.025em; }
        .summary-sub { color: var(--muted); display: block; font-size: 0.86rem; margin-top: 0.28rem; }
        .summary-tag {
            background: #f6f8fb;
            border: 1px solid var(--line);
            border-radius: 12px;
            color: var(--muted);
            font-size: 0.74rem;
            font-weight: 720;
            padding: 0.45rem 0.7rem;
            text-transform: uppercase;
        }
        .kpi-grid {
            display: grid;
            gap: 1rem;
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }
        .kpi-tile {
            border-radius: 18px;
            min-height: 8.4rem;
            padding: 1.05rem 1.05rem 0.95rem;
        }
        .kpi-tile--blue { background: #eaf4ff; }
        .kpi-tile--rose { background: #ffe8ec; }
        .kpi-tile--amber { background: #fff4dc; }
        .kpi-tile--green { background: #ddf8e8; }
        .kpi-label {
            color: #6f7791;
            display: block;
            font-size: 0.78rem;
            font-weight: 760;
            line-height: 1.2;
        }
        .kpi-value {
            color: var(--ink);
            display: block;
            font-size: clamp(1.35rem, 1.55vw, 1.95rem);
            font-variant-numeric: tabular-nums;
            font-weight: 830;
            letter-spacing: -0.04em;
            line-height: 1.05;
            margin-top: 1.2rem;
            overflow-wrap: anywhere;
        }
        .kpi-delta {
            color: #4c8d7c;
            display: block;
            font-size: 0.76rem;
            font-weight: 760;
            margin-top: 0.7rem;
        }

        .refund-card, .insight-preview-card {
            background: var(--surface);
            border: 1px solid rgba(232, 236, 243, 0.88);
            border-radius: 24px;
            box-shadow: var(--shadow);
            height: 100%;
            padding: 1.3rem 1.35rem;
        }
        .refund-meter {
            background: #edf2f6;
            border-radius: 999px;
            height: 0.7rem;
            margin: 1rem 0 0.8rem;
            overflow: hidden;
        }
        .refund-meter span {
            background: linear-gradient(90deg, var(--amber), #eab75f);
            border-radius: inherit;
            display: block;
            height: 100%;
        }
        .mini-stat {
            align-items: baseline;
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.55rem 0;
        }
        .mini-stat + .mini-stat { border-top: 1px solid var(--line); }
        .mini-stat span:first-child { color: var(--muted); font-size: 0.8rem; font-weight: 700; }
        .mini-stat span:last-child {
            color: var(--ink);
            font-size: 0.95rem;
            font-variant-numeric: tabular-nums;
            font-weight: 800;
            text-align: right;
        }
        .preview-stack { display: flex; flex-direction: column; gap: 0.8rem; margin-top: 0.8rem; }
        .preview-item {
            background: #f7f9fb;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 0.88rem 0.95rem;
        }
        .preview-kind {
            color: var(--accent-dark);
            display: block;
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            margin-bottom: 0.4rem;
            text-transform: uppercase;
        }
        .preview-text {
            color: var(--ink);
            display: block;
            font-size: 0.84rem;
            line-height: 1.48;
        }

        /* ---- Visual insight cards ---- */
        .insight-card {
            display: block;
            background: var(--surface);
            border: 1px solid var(--line);
            border-left: 4px solid var(--accent);
            border-radius: 12px;
            box-shadow: var(--shadow);
            padding: 1.15rem 1.25rem;
            height: 100%;
        }
        .insight-card.tone-risk { border-left-color: #9d5d28; }
        .insight-card.tone-trend { border-left-color: #4e7fa1; }
        .insight-card.tone-structure { border-left-color: #b2863f; }
        .insight-card.tone-adjustment { border-left-color: #738b4f; }
        .insight-card.tone-conclusion { border-left-color: #7a6aa0; }

        .insight-card .ic-body { display: flex; flex-direction: column; gap: 0.45rem; }
        .insight-card .ic-kind {
            align-self: flex-start;
            background: var(--surface-strong);
            border: 1px solid rgba(217, 223, 220, 0.95);
            border-radius: 7px;
            color: var(--muted);
            font-size: 0.66rem;
            font-weight: 760;
            letter-spacing: 0.05em;
            padding: 0.18rem 0.5rem;
            text-transform: uppercase;
        }
        .insight-card .ic-text {
            color: var(--ink);
            font-size: 0.94rem;
            line-height: 1.58;
            text-wrap: pretty;
        }
        .insight-card .ic-text b { color: var(--accent-dark); }

        @media (max-width: 980px) {
            .stat-grid { grid-template-columns: repeat(3, 1fr); }
            .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .page-title-bar { align-items: flex-start; flex-direction: column; }
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .metric-value {
                font-size: 1.45rem;
            }
            .kpi-grid { grid-template-columns: 1fr; }
            .summary-panel, .refund-card, .insight-preview-card {
                border-radius: 20px;
                padding: 1.05rem;
            }

            .section-heading {
                align-items: start;
                flex-direction: column;
            }

            .brand-sub {
                display: none;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_php(value):
    """Format numeric values as Philippine peso amounts."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"PHP {value:,.2f}"


def format_compact_php(value):
    """Format large peso values for compact dashboard tiles."""
    if value is None or pd.isna(value):
        return "N/A"
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    if abs_value >= 1_000_000:
        return f"{sign}PHP {abs_value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"{sign}PHP {abs_value / 1_000:.1f}K"
    return f"{sign}PHP {abs_value:,.0f}"


def format_number(value):
    """Format count values with thousands separators."""
    if value is None or pd.isna(value):
        return "0"
    return f"{int(value):,}"


def section_heading(title, description):
    """Render a consistent section heading."""
    st.markdown(
        f"""
        <div class="section-heading">
            <h2>{escape(title)}</h2>
            <span>{escape(description)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data
def load_processed_analysis_outputs():
    """Load saved processed analysis CSV outputs for dashboard display."""
    return load_analysis_outputs()


@st.cache_data
def load_processed_financial_analysis():
    """Load the full processed analysis dictionary when preprocessing exists."""
    try:
        return get_preprocessed_financial_analysis()
    except (FileNotFoundError, KeyError, pd.errors.EmptyDataError):
        return {}


def _numeric_series(df, column):
    """Return a numeric series for a column that may be absent."""
    if df is None or df.empty or column not in df.columns:
        return pd.Series(dtype="float64")
    return pd.to_numeric(df[column], errors="coerce").dropna()


def _sum_column(df, column):
    """Return a numeric column total from a possibly empty dataframe."""
    values = _numeric_series(df, column)
    return float(values.sum()) if not values.empty else 0.0


def _mean_column(df, column):
    """Return a numeric column mean from a possibly empty dataframe."""
    values = _numeric_series(df, column)
    return float(values.mean()) if not values.empty else None


def build_processed_display_summary(
    analysis_outputs,
    processed_analysis,
    fallback_summary,
):
    """Adapt processed analysis outputs to the existing dashboard summary shape."""
    monthly_df = analysis_outputs.get("monthly_summary", pd.DataFrame())
    category_df = analysis_outputs.get("category_summary", pd.DataFrame())
    budget_df = analysis_outputs.get("budget_variance_summary", pd.DataFrame())
    health_df = analysis_outputs.get("financial_health_summary", pd.DataFrame())
    expense_group_df = analysis_outputs.get("expense_group_summary", pd.DataFrame())
    processed_available = any(not frame.empty for frame in analysis_outputs.values())
    if not processed_available:
        return fallback_summary

    summary = dict(fallback_summary)
    totals = processed_analysis.get("totals", {})
    overview = processed_analysis.get("dataset_overview", {})
    stats = processed_analysis.get("statistical_analysis", {})
    health_summary = processed_analysis.get("financial_health_score_summary", {})
    emergency = processed_analysis.get(
        "emergency_fund_contribution_consistency", {}
    )

    total_income = totals.get("total_income", _sum_column(monthly_df, "total_income"))
    total_expenses = totals.get(
        "total_expenses", _sum_column(monthly_df, "total_expenses")
    )
    total_savings = totals.get(
        "total_savings", _sum_column(monthly_df, "total_savings")
    )
    total_debt = totals.get(
        "total_debt_payments", _sum_column(monthly_df, "total_debt_payments")
    )

    budget_total = _sum_column(budget_df, "total_budget")
    budget_spent = _sum_column(budget_df, "total_spent")
    budget_usage = (budget_spent / budget_total * 100) if budget_total else 0.0

    latest_health_score = None
    if not health_df.empty and "financial_health_score" in health_df.columns:
        health_scores = pd.to_numeric(
            health_df["financial_health_score"], errors="coerce"
        ).dropna()
        if not health_scores.empty:
            latest_health_score = float(health_scores.iloc[-1])

    category_totals = {}
    if not category_df.empty and {"category", "total_spent"}.issubset(category_df):
        category_totals = (
            category_df.assign(
                total_spent=pd.to_numeric(
                    category_df["total_spent"], errors="coerce"
                )
            )
            .dropna(subset=["total_spent"])
            .sort_values("total_spent", ascending=False)
            .set_index("category")["total_spent"]
            .round(2)
            .to_dict()
        )

    budget_by_category = {}
    if not budget_df.empty and {"category", "total_spent", "total_budget"}.issubset(
        budget_df
    ):
        budget_table = budget_df.copy()
        budget_table["total_spent"] = pd.to_numeric(
            budget_table["total_spent"], errors="coerce"
        ).fillna(0)
        budget_table["total_budget"] = pd.to_numeric(
            budget_table["total_budget"], errors="coerce"
        ).fillna(0)
        budget_table["remaining_budget"] = (
            budget_table["total_budget"] - budget_table["total_spent"]
        )
        budget_table["usage_percent"] = budget_table.apply(
            lambda row: (row["total_spent"] / row["total_budget"] * 100)
            if row["total_budget"]
            else 0,
            axis=1,
        )
        budget_by_category = (
            budget_table.set_index("category")[
                ["total_spent", "total_budget", "remaining_budget", "usage_percent"]
            ]
            .round(2)
            .to_dict(orient="index")
        )

    monthly_trends = {}
    if not monthly_df.empty and "year_month" in monthly_df.columns:
        monthly_table = monthly_df.copy()
        numeric_columns = [
            column for column in monthly_table.columns if column != "year_month"
        ]
        for column in numeric_columns:
            monthly_table[column] = pd.to_numeric(
                monthly_table[column], errors="coerce"
            )
        monthly_table["gross_expense_total"] = monthly_table.get("total_expenses")
        monthly_table["net_amount"] = monthly_table.get("total_expenses")
        monthly_table["refund_total"] = 0.0
        monthly_table["average_transaction"] = None
        monthly_table["transaction_count"] = None
        monthly_trends = (
            monthly_table.set_index("year_month").round(2).to_dict(orient="index")
        )

    summary.update(
        {
            "is_processed_summary": True,
            "processed_outputs_available": processed_available,
            "dataset_overview": overview,
            "processed_statistics": stats,
            "financial_health_summary": health_summary,
            "emergency_fund_summary": emergency,
            "total_transactions": overview.get(
                "processed_transaction_rows",
                fallback_summary.get("total_transactions", 0),
            ),
            "gross_expense_total": total_expenses,
            "net_amount": total_expenses,
            "refund_total": 0.0,
            "refund_transactions": 0,
            "total_income": total_income,
            "total_savings": total_savings,
            "total_debt_payments": total_debt,
            "latest_financial_health_score": latest_health_score,
            "average_savings_rate": _mean_column(monthly_df, "savings_rate"),
            "average_debt_ratio": _mean_column(monthly_df, "debt_ratio"),
            "category_totals": category_totals,
            "monthly_trends": monthly_trends,
            "budget_summary": {
                "total_budget": budget_total,
                "total_spent": budget_spent,
                "total_expenses": budget_spent,
                "remaining_budget": budget_total - budget_spent,
                "budget_usage_percent": budget_usage,
            },
            "budget_by_category": budget_by_category,
            "expense_group_summary": expense_group_df,
        }
    )
    return summary


def show_financial_summary_panel(summary):
    """Render the reference-style grouped financial KPI panel."""
    budget_summary = summary.get("budget_summary", {})
    budget_usage = budget_summary.get("budget_usage_percent", 0)
    if summary.get("is_processed_summary"):
        health_score = summary.get("latest_financial_health_score")
        tiles = [
            (
                "Total income",
                format_compact_php(summary.get("total_income")),
                "Processed monthly income",
                "green",
            ),
            (
                "Total expenses",
                format_compact_php(summary.get("gross_expense_total")),
                "Processed expense total",
                "rose",
            ),
            (
                "Total savings",
                format_compact_php(summary.get("total_savings")),
                "Savings transactions",
                "blue",
            ),
            (
                "Health score",
                f"{health_score:.1f}" if health_score is not None else "N/A",
                "Latest monthly score",
                "green" if (health_score or 0) >= 70 else "amber",
            ),
        ]
    else:
        tiles = [
            (
                "Total expenses",
                format_compact_php(summary.get("gross_expense_total")),
                "Positive expense transactions",
                "rose",
            ),
            (
                "Refunds",
                format_compact_php(summary.get("refund_total")),
                f"{format_number(summary.get('refund_transactions', 0))} refunded records",
                "amber",
            ),
            (
                "Net amount",
                format_compact_php(summary.get("net_amount")),
                "Expenses after refund adjustment",
                "blue",
            ),
            (
                "Budget used",
                f"{budget_usage:.1f}%",
                "Monthly category budget",
                "green" if budget_usage <= 100 else "rose",
            ),
        ]
    tiles_html = "".join(
        f"""
        <div class="kpi-tile kpi-tile--{escape(tone)}">
            <span class="kpi-label">{escape(label)}</span>
            <span class="kpi-value">{escape(value)}</span>
            <span class="kpi-delta">{escape(detail)}</span>
        </div>
        """
        for label, value, detail, tone in tiles
    )
    summary_sub = (
        "Processed outputs converted into decision metrics"
        if summary.get("is_processed_summary")
        else "Filtered records converted into decision metrics"
    )
    st.markdown(
        f"""
        <div class="summary-panel">
            <div class="summary-head">
                <div>
                    <span class="summary-title">Financial summary</span>
                    <span class="summary-sub">{escape(summary_sub)}</span>
                </div>
                <span class="summary-tag">{format_number(summary.get("total_transactions", 0))} transactions</span>
            </div>
            <div class="kpi-grid">{tiles_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_refund_impact_card(summary):
    """Render a compact card showing how refunds affect the net amount."""
    if summary.get("is_processed_summary"):
        total_income = summary.get("total_income", 0) or 0
        total_savings = summary.get("total_savings", 0) or 0
        total_debt = summary.get("total_debt_payments", 0) or 0
        savings_rate = (total_savings / total_income * 100) if total_income else 0
        debt_ratio = (total_debt / total_income * 100) if total_income else 0
        meter_width = min(savings_rate, 100)
        st.markdown(
            f"""
            <div class="refund-card">
                <span class="bento-title">Savings and debt</span>
                <div class="bento-sub">Processed savings and debt payment ratios</div>
                <div class="refund-meter"><span style="width:{meter_width:.1f}%"></span></div>
                <div class="mini-stat"><span>Savings rate</span><span>{savings_rate:.1f}%</span></div>
                <div class="mini-stat"><span>Debt ratio</span><span>{debt_ratio:.1f}%</span></div>
                <div class="mini-stat"><span>Debt payments</span><span>{escape(format_php(total_debt))}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    total_expenses = summary.get("gross_expense_total", 0) or 0
    refund_total = summary.get("refund_total", 0) or 0
    net_amount = summary.get("net_amount", 0)
    refund_share = (refund_total / total_expenses * 100) if total_expenses else 0
    meter_width = min(refund_share, 100)
    st.markdown(
        f"""
        <div class="refund-card">
            <span class="bento-title">Refund impact</span>
            <div class="bento-sub">Gross expenses compared with net cash impact</div>
            <div class="refund-meter"><span style="width:{meter_width:.1f}%"></span></div>
            <div class="mini-stat"><span>Refund share</span><span>{refund_share:.1f}%</span></div>
            <div class="mini-stat"><span>Refund total</span><span>{escape(format_php(refund_total))}</span></div>
            <div class="mini-stat"><span>Net amount</span><span>{escape(format_php(net_amount))}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_top_categories_table(summary, limit=5):
    """Render the ranked category table used on the Overview dashboard."""
    category_totals = list(summary.get("category_totals", {}).items())[:limit]
    total_expenses = summary.get("gross_expense_total", 0) or 0
    budget_by_category = summary.get("budget_by_category", {})
    rows = []
    for index, (category, amount) in enumerate(category_totals, start=1):
        share = (amount / total_expenses * 100) if total_expenses else 0
        budget_usage = budget_by_category.get(category, {}).get("usage_percent", 0)
        rows.append(
            {
                "#": f"{index:02d}",
                "Category": str(category),
                "Expenses": amount,
                "Share": share,
                "Budget used": budget_usage,
            }
        )
    table_df = pd.DataFrame(rows)
    max_budget_usage = max(100, float(table_df["Budget used"].max())) if not table_df.empty else 100
    with st.container(border=True):
        st.markdown(
            """
            <span class="bento-title">Top categories</span>
            <div class="bento-sub">Ranked by positive expense total</div>
            """,
            unsafe_allow_html=True,
        )
        if table_df.empty:
            st.info("Top categories are unavailable for the selected data.")
        else:
            st.dataframe(
                table_df,
                width="stretch",
                hide_index=True,
                column_config={
                    "Expenses": st.column_config.NumberColumn(
                        "Expenses", format="PHP %.2f"
                    ),
                    "Share": st.column_config.ProgressColumn(
                        "Share",
                        format="%.1f%%",
                        min_value=0,
                        max_value=100,
                    ),
                    "Budget used": st.column_config.ProgressColumn(
                        "Budget used",
                        format="%.1f%%",
                        min_value=0,
                        max_value=max_budget_usage,
                    ),
                },
            )


def parse_insight(item):
    """Split a generated insight into label, tone, and body."""
    prefix, sep, rest = item.partition(":")
    if sep and prefix.strip() in INSIGHT_STYLE:
        tone, kind = INSIGHT_STYLE[prefix.strip()]
        return tone, kind, rest.strip()
    return "", "Insight", item


def show_insight_preview(df, summary=None, limit=3):
    """Render the first few analytical findings for the Overview page."""
    if summary and summary.get("is_processed_summary"):
        budget_rows = summary.get("budget_by_category", {})
        highest_overspend = None
        if budget_rows:
            highest_overspend = max(
                budget_rows.items(),
                key=lambda item: item[1].get("total_spent", 0)
                - item[1].get("total_budget", 0),
            )
        health_score = summary.get("latest_financial_health_score")
        savings_rate = summary.get("average_savings_rate")
        debt_ratio = summary.get("average_debt_ratio")
        processed_items = []
        if highest_overspend:
            category, values = highest_overspend
            variance = values.get("total_spent", 0) - values.get("total_budget", 0)
            processed_items.append(
                (
                    "tone-risk" if variance > 0 else "tone-structure",
                    "Budget variance",
                    f"{category} variance is {format_php(variance)}.",
                )
            )
        if health_score is not None:
            processed_items.append(
                (
                    "tone-trend",
                    "Financial health",
                    f"Latest financial health score is {health_score:.2f} out of 100.",
                )
            )
        if savings_rate is not None and debt_ratio is not None:
            processed_items.append(
                (
                    "tone-conclusion",
                    "Savings and debt",
                    f"Average savings rate is {savings_rate:.2f}% while average debt ratio is {debt_ratio:.2f}%.",
                )
            )
        items = processed_items[:limit]
    else:
        items = [parse_insight(item) for item in generate_insights(df)[:limit]]
    cards_html = "".join(
        f"""
        <div class="preview-item">
            <span class="preview-kind">{escape(kind)}</span>
            <span class="preview-text">{_highlight_numbers(text)}</span>
        </div>
        """
        for _, kind, text in items
    )
    st.markdown(
        f"""
        <div class="insight-preview-card">
            <span class="bento-title">Analytical priorities</span>
            <div class="bento-sub">Highest-signal findings from the filtered data</div>
            <div class="preview-stack">{cards_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_brand():
    """Render the brand block at the top of the sidebar."""
    st.sidebar.markdown(
        """
        <div class="sb-brand">
            <div class="brand-text">
                <span class="brand-name">FinSys</span>
                <span class="brand-sub">Financial Monitoring</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_title(page, total_rows=None, showing=None):
    """Render the dashboard header."""
    st.markdown(
        f"""
        <div class="page-title-bar">
            <div class="pt-left">
                <h1 class="pt-title">{escape(page)}</h1>
                <span class="pt-meta">Financial expense monitoring dashboard</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def filter_dataset(df):
    """Apply sidebar filters to the cleaned dataset."""
    filtered_df = df.copy()

    st.sidebar.markdown("#### Filters")
    st.sidebar.caption("Refine the records used by every metric, chart, and insight.")

    if "date" in filtered_df.columns:
        filtered_df["date"] = pd.to_datetime(filtered_df["date"], errors="coerce")
        valid_dates = filtered_df["date"].dropna()
        if not valid_dates.empty:
            selected_dates = st.sidebar.date_input(
                "Date range",
                value=(valid_dates.min().date(), valid_dates.max().date()),
                min_value=valid_dates.min().date(),
                max_value=valid_dates.max().date(),
            )
            if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
                start_date, end_date = selected_dates
                filtered_df = filtered_df[
                    (filtered_df["date"].dt.date >= start_date)
                    & (filtered_df["date"].dt.date <= end_date)
                ]

    categorical_columns = [
        column
        for column in [
            "account_type",
            "category",
            "payment_method",
            "status",
            "necessity_type",
        ]
        if column in filtered_df.columns
    ]

    if categorical_columns:
        with st.sidebar.expander("Account & categories", expanded=False):
            st.caption("Leave a field empty to include all values.")
            for column in categorical_columns:
                options = sorted(filtered_df[column].dropna().astype(str).unique())
                selected_options = st.multiselect(
                    column.replace("_", " ").title(),
                    options,
                    default=[],
                    placeholder="All",
                )
                if selected_options:
                    filtered_df = filtered_df[
                        filtered_df[column].astype(str).isin(selected_options)
                    ]

    return filtered_df


def show_statistics(summary):
    """Render the full statistical summary required by the rubric."""
    if summary.get("is_processed_summary"):
        stats = summary.get("processed_statistics", {})
        health = summary.get("financial_health_summary", {})
        emergency = summary.get("emergency_fund_summary", {})
        tiles = [
            (
                "Average monthly expense",
                format_php(stats.get("average_monthly_expense")),
            ),
            (
                "Median transaction",
                format_php(stats.get("median_transaction_amount")),
            ),
            (
                "Std. monthly expenses",
                format_php(stats.get("standard_deviation_of_monthly_expenses")),
            ),
            (
                "Average savings rate",
                f"{summary.get('average_savings_rate'):.2f}%"
                if summary.get("average_savings_rate") is not None
                else "N/A",
            ),
            (
                "Average health score",
                f"{health.get('average_financial_health_score'):.2f}"
                if health.get("average_financial_health_score") is not None
                else "N/A",
            ),
            (
                "Emergency consistency",
                f"{emergency.get('consistency_rate_percent'):.2f}%"
                if emergency.get("consistency_rate_percent") is not None
                else "N/A",
            ),
        ]
    else:
        stats = summary.get("amount_statistics", {})
        tiles = [
            ("Mean transaction", format_php(stats.get("mean"))),
            ("Median transaction", format_php(stats.get("median"))),
            ("Mode transaction", format_php(stats.get("mode"))),
            ("Std. deviation", format_php(stats.get("standard_deviation"))),
            ("Largest refund", format_php(stats.get("largest_refund_abs"))),
            ("Largest transaction", format_php(stats.get("largest_transaction"))),
        ]
    tiles_html = "".join(
        f'<div class="stat-tile"><span class="stat-label">{escape(label)}</span>'
        f'<span class="stat-value">{escape(value)}</span></div>'
        for label, value in tiles
    )
    st.markdown(f'<div class="stat-grid">{tiles_html}</div>', unsafe_allow_html=True)


def show_cleaning_report(raw_df, cleaned_df, filtered_df):
    """Summarize the cleaning pipeline outcome for the rubric's cleaning criterion."""
    raw_rows = raw_df.shape[0]
    cleaned_rows = cleaned_df.shape[0]
    removed_rows = raw_rows - cleaned_rows

    cleaning_cols = st.columns(4)
    cleaning_cols[0].metric("Raw rows", f"{raw_rows:,}")
    cleaning_cols[1].metric("Cleaned rows", f"{cleaned_rows:,}")
    cleaning_cols[2].metric(
        "Rows removed",
        f"{removed_rows:,}",
        delta=f"-{(removed_rows / raw_rows * 100):.1f}%" if raw_rows else None,
        delta_color="inverse",
    )
    cleaning_cols[3].metric("Filtered rows", f"{filtered_df.shape[0]:,}")

    raw_duplicates = int(raw_df.duplicated().sum())
    raw_missing = int(raw_df.isna().sum().sum())
    cleaned_missing = int(cleaned_df.isna().sum().sum())

    steps = [
        ("Duplicate rows removed", f"{raw_duplicates:,} exact duplicate rows dropped"),
        (
            "Missing values handled",
            f"{raw_missing:,} blanks in raw data \u2192 {cleaned_missing:,} remaining after filling/dropping",
        ),
        (
            "Inconsistent entries standardized",
            "Categories, payment methods, and statuses mapped to consistent labels",
        ),
        (
            "Data types converted",
            "Dates parsed to datetime, amounts/budgets to numeric, categories to category dtype",
        ),
        (
            "Invalid records filtered",
            "Rows with unparseable dates or missing amounts removed; suspicious amounts flagged for review",
        ),
    ]
    report_html = "".join(
        f'<div class="insight-item"><strong>{escape(title)}.</strong> {escape(detail)}</div>'
        for title, detail in steps
    )
    st.markdown(report_html, unsafe_allow_html=True)


def load_project_dataset():
    """Load the fixed project dataset from data/raw."""
    return load_raw_dataset()


def show_analysis_tables(summary, df, analysis_outputs=None):
    """Display grouped analysis tables in tabs."""
    analysis_outputs = analysis_outputs or {}
    export_col, _ = st.columns([1, 3])
    with export_col:
        if st.button("Export summary CSVs", width="stretch"):
            if summary.get("is_processed_summary"):
                exported_paths = save_analysis_summaries()
                load_processed_analysis_outputs.clear()
                load_processed_financial_analysis.clear()
            else:
                exported_paths = export_summary_csvs(df)
            st.session_state["exported_summary_paths"] = exported_paths

    exported_paths = st.session_state.get("exported_summary_paths")
    if exported_paths:
        st.success(
            "Summary CSVs saved to `data/outputs/processed/analysis/`: "
            + ", ".join(f"`{path.name}`" for path in exported_paths.values())
        )
        download_cols = st.columns(len(exported_paths))
        for col, (name, path) in zip(download_cols, exported_paths.items()):
            with col:
                st.download_button(
                    f"Download {name}",
                    path.read_bytes(),
                    file_name=path.name,
                    key=f"download_{path.name}",
                    width="stretch",
                )

    st.write("")
    section_heading(
        "Statistical summary",
        "Processed monthly, transaction, emergency fund, and health score metrics.",
    )
    show_statistics(summary)
    st.write("")

    tabs = st.tabs(
        [
            "Category totals",
            "Monthly trends",
            "Budget summary",
            "Financial health",
            "Expense groups",
        ]
    )

    with tabs[0]:
        category_df = analysis_outputs.get("category_summary", pd.DataFrame())
        if not category_df.empty:
            st.dataframe(
                category_df,
                width='stretch',
                hide_index=True,
                column_config={
                    "total_spent": st.column_config.NumberColumn(
                        "Total Expenses", format="PHP %.2f"
                    ),
                    "average_transaction": st.column_config.NumberColumn(
                        "Average Transaction", format="PHP %.2f"
                    ),
                    "pct_of_expenses": st.column_config.NumberColumn(
                        "Share", format="%.2f%%"
                    ),
                },
            )
        else:
            category_totals = summary.get("category_totals", {})
            if category_totals:
                fallback_category_df = pd.DataFrame(
                    category_totals.items(), columns=["Category", "Total Expenses"]
                )
                st.dataframe(
                    fallback_category_df,
                    width='stretch',
                    hide_index=True,
                    column_config={
                        "Total Expenses": st.column_config.NumberColumn(
                            "Total Expenses", format="PHP %.2f"
                        )
                    },
                )
            else:
                st.info("Category totals are unavailable for the selected data.")

    with tabs[1]:
        monthly_df = analysis_outputs.get("monthly_summary", pd.DataFrame())
        if not monthly_df.empty:
            st.dataframe(
                monthly_df,
                width='stretch',
                hide_index=True,
                column_config={
                    "total_income": st.column_config.NumberColumn(
                        "Total Income", format="PHP %.2f"
                    ),
                    "total_expenses": st.column_config.NumberColumn(
                        "Total Expenses", format="PHP %.2f"
                    ),
                    "total_savings": st.column_config.NumberColumn(
                        "Total Savings", format="PHP %.2f"
                    ),
                    "total_debt_payments": st.column_config.NumberColumn(
                        "Debt Payments", format="PHP %.2f"
                    ),
                    "savings_rate": st.column_config.NumberColumn(
                        "Savings Rate", format="%.2f%%"
                    ),
                    "income_to_expense_ratio": st.column_config.NumberColumn(
                        "Income/Expense Ratio", format="%.2f"
                    ),
                    "debt_ratio": st.column_config.NumberColumn(
                        "Debt Ratio", format="%.2f%%"
                    ),
                },
            )
        else:
            monthly_trends = summary.get("monthly_trends", {})
            if monthly_trends:
                fallback_monthly_df = pd.DataFrame.from_dict(
                    monthly_trends, orient="index"
                )
                fallback_monthly_df.index.name = "Month"
                st.dataframe(fallback_monthly_df.reset_index(), width='stretch')
            else:
                st.info("Monthly trends are unavailable for the selected data.")

    with tabs[2]:
        budget_df = analysis_outputs.get("budget_variance_summary", pd.DataFrame())
        if not budget_df.empty:
            st.dataframe(
                budget_df,
                width='stretch',
                hide_index=True,
                column_config={
                    "total_spent": st.column_config.NumberColumn(
                        "Total Expenses", format="PHP %.2f"
                    ),
                    "total_budget": st.column_config.NumberColumn(
                        "Total Budget", format="PHP %.2f"
                    ),
                    "budget_variance": st.column_config.NumberColumn(
                        "Budget Variance", format="PHP %.2f"
                    ),
                    "variance_percent": st.column_config.NumberColumn(
                        "Variance", format="%.2f%%"
                    ),
                },
            )
        else:
            budget_by_category = summary.get("budget_by_category", {})
            if budget_by_category:
                fallback_budget_df = pd.DataFrame.from_dict(
                    budget_by_category, orient="index"
                )
                fallback_budget_df.index.name = "Category"
                st.dataframe(fallback_budget_df.reset_index(), width='stretch')
            else:
                st.info("Budget summaries are unavailable for the selected data.")

    with tabs[3]:
        health_df = analysis_outputs.get("financial_health_summary", pd.DataFrame())
        if not health_df.empty:
            st.dataframe(
                health_df,
                width='stretch',
                hide_index=True,
                column_config={
                    "total_income": st.column_config.NumberColumn(
                        "Total Income", format="PHP %.2f"
                    ),
                    "total_expenses": st.column_config.NumberColumn(
                        "Total Expenses", format="PHP %.2f"
                    ),
                    "total_savings": st.column_config.NumberColumn(
                        "Total Savings", format="PHP %.2f"
                    ),
                    "total_debt_payments": st.column_config.NumberColumn(
                        "Debt Payments", format="PHP %.2f"
                    ),
                    "financial_health_score": st.column_config.NumberColumn(
                        "Health Score", format="%.2f"
                    ),
                    "savings_score": st.column_config.NumberColumn(
                        "Savings Score", format="%.2f"
                    ),
                    "debt_score": st.column_config.NumberColumn(
                        "Debt Score", format="%.2f"
                    ),
                    "budget_balance_score": st.column_config.NumberColumn(
                        "Budget Balance Score", format="%.2f"
                    ),
                    "emergency_fund_score": st.column_config.NumberColumn(
                        "Emergency Fund Score", format="%.2f"
                    ),
                },
            )
        else:
            st.info("Financial health summaries are unavailable.")

    with tabs[4]:
        expense_group_df = analysis_outputs.get("expense_group_summary", pd.DataFrame())
        if not expense_group_df.empty:
            st.dataframe(
                expense_group_df,
                width='stretch',
                hide_index=True,
                column_config={
                    "total_spent": st.column_config.NumberColumn(
                        "Total Spent", format="PHP %.2f"
                    ),
                    "average_transaction": st.column_config.NumberColumn(
                        "Average Transaction", format="PHP %.2f"
                    ),
                    "pct_of_expenses": st.column_config.NumberColumn(
                        "Share", format="%.2f%%"
                    ),
                },
            )
        else:
            st.info("Expense group summaries are unavailable.")


def show_charts(df, analysis_outputs=None):
    """Display visualization charts in a two-column layout."""
    charts = (
        create_analysis_visualization_charts(analysis_outputs)
        if analysis_outputs
        else create_visualization_charts(df)
    )

    chart_items = [(title, fig) for title, fig in charts.items() if fig is not None]
    if not chart_items:
        st.info("Charts are unavailable for the selected data.")
        return

    chart_config = {"displayModeBar": False, "responsive": True}
    for index in range(0, len(chart_items), 2):
        cols = st.columns(2, gap="large")
        for col, (title, fig) in zip(cols, chart_items[index : index + 2]):
            with col:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="bento-title">{escape(title)}</div>',
                        unsafe_allow_html=True,
                    )
                    if hasattr(fig, "to_plotly_json"):
                        st.plotly_chart(fig, width='stretch', config=chart_config)
                    else:
                        st.pyplot(fig, width='stretch')


def bento_chart(title, sub, fig, config):
    """Render a chart inside a bordered bento card."""
    with st.container(border=True):
        st.markdown(
            f'<div class="bento-title">{escape(title)}</div>'
            f'<div class="bento-sub">{escape(sub)}</div>',
            unsafe_allow_html=True,
        )
        if fig is not None:
            st.plotly_chart(fig, width='stretch', config=config)
        else:
            st.info("Not available for the selected data.")


def show_overview(summary, df, analysis_outputs=None):
    """Render the Overview page as a reference-style dashboard grid."""
    config = {"displayModeBar": False, "responsive": True}
    budget_summary = summary.get("budget_summary", {})
    analysis_outputs = analysis_outputs or {}

    summary_col, trend_col = st.columns([1.55, 1], gap="large")
    with summary_col:
        show_financial_summary_panel(summary)
    with trend_col:
        bento_chart(
            "Income vs expenses",
            "Processed monthly income and expense totals",
            create_monthly_income_expenses_line(
                analysis_outputs.get("monthly_summary", pd.DataFrame())
            )
            if summary.get("is_processed_summary")
            else create_mini_monthly_line(df),
            config,
        )

    st.write("")
    category_col, refund_col, budget_col = st.columns([1.35, 0.9, 0.95], gap="large")
    with category_col:
        bento_chart(
            "Category expenses",
            "Top categories by processed expense amount",
            create_expenses_by_category_bar(
                analysis_outputs.get("category_summary", pd.DataFrame()), top_n=6
            )
            if summary.get("is_processed_summary")
            else create_top_categories_bar(df, top_n=6),
            config,
        )
    with refund_col:
        show_refund_impact_card(summary)
    with budget_col:
        bento_chart(
            "Budget usage",
            "Expenses vs monthly category budget",
            create_budget_gauge(budget_summary.get("budget_usage_percent")),
            config,
        )

    st.write("")
    budget_wide_col, insight_col = st.columns([1.45, 1], gap="large")
    with budget_wide_col:
        bento_chart(
            "Budget vs expenses",
            "Processed category variance against budget",
            create_budget_variance_by_category_bar(
                analysis_outputs.get("budget_variance_summary", pd.DataFrame())
            )
            if summary.get("is_processed_summary")
            else create_budget_vs_actual_chart(df),
            config,
        )
    with insight_col:
        show_insight_preview(df, summary)

    st.write("")
    show_top_categories_table(summary)


INSIGHT_STYLE = {
    "Budget variance": ("tone-risk", "Budget variance"),
    "Budget exposure": ("tone-risk", "Budget exposure"),
    "Category concentration": ("tone-structure", "Category concentration"),
    "Refund adjustment": ("tone-adjustment", "Refund adjustment"),
    "Peak period": ("tone-trend", "Peak period"),
    "Monthly volatility": ("tone-trend", "Monthly volatility"),
    "Priority mix": ("tone-structure", "Priority mix"),
    "Analytical conclusion": ("tone-conclusion", "Analytical conclusion"),
}


def _highlight_numbers(text):
    """Bold peso amounts and percentages inside escaped insight text."""
    safe = escape(text)
    safe = re.sub(r"(PHP\s-?[\d,]+\.\d{2})", r"<b>\1</b>", safe)
    safe = re.sub(r"(\d+\.\d+%)", r"<b>\1</b>", safe)
    return safe


def show_visual_insights(df, summary=None):
    """Render action-first insights as visual cards."""
    section_heading(
        "Analytical findings",
        "Evidence-based interpretation of budget variance, spending concentration, refunds, and monthly movement.",
    )

    cards = []
    if summary and summary.get("is_processed_summary"):
        health = summary.get("financial_health_summary", {})
        emergency = summary.get("emergency_fund_summary", {})
        budget_rows = summary.get("budget_by_category", {})

        if budget_rows:
            category, values = max(
                budget_rows.items(),
                key=lambda item: item[1].get("total_spent", 0)
                - item[1].get("total_budget", 0),
            )
            variance = values.get("total_spent", 0) - values.get("total_budget", 0)
            cards.append(
                (
                    "tone-risk" if variance > 0 else "tone-structure",
                    "Budget variance",
                    f"{category} has the largest processed budget variance at {format_php(variance)}.",
                )
            )

        latest_score = summary.get("latest_financial_health_score")
        average_score = health.get("average_financial_health_score")
        if latest_score is not None:
            average_score_text = (
                f"{average_score:.2f}" if average_score is not None else "N/A"
            )
            cards.append(
                (
                    "tone-trend",
                    "Financial health",
                    f"Latest score is {latest_score:.2f}; average score across observed months is {average_score_text}.",
                )
            )

        savings_rate = summary.get("average_savings_rate")
        debt_ratio = summary.get("average_debt_ratio")
        if savings_rate is not None and debt_ratio is not None:
            cards.append(
                (
                    "tone-conclusion",
                    "Savings and debt",
                    f"Average savings rate is {savings_rate:.2f}% and average debt ratio is {debt_ratio:.2f}% from processed monthly summaries.",
                )
            )

        consistency = emergency.get("consistency_rate_percent")
        months_with = emergency.get("months_with_contribution")
        months_total = emergency.get("months_observed")
        if consistency is not None:
            cards.append(
                (
                    "tone-structure",
                    "Emergency fund",
                    f"Emergency fund contributions appear in {months_with} of {months_total} months, a {consistency:.2f}% consistency rate.",
                )
            )
    else:
        for item in generate_insights(df):
            prefix, sep, rest = item.partition(":")
            if sep and prefix.strip() in INSIGHT_STYLE:
                tone, kind = INSIGHT_STYLE[prefix.strip()]
                text = rest.strip()
            else:
                tone, kind = "", "Insight"
                text = item
            cards.append((tone, kind, text))

    for index in range(0, len(cards), 2):
        cols = st.columns(2, gap="large")
        for col, (tone, kind, text) in zip(cols, cards[index : index + 2]):
            with col:
                st.markdown(
                    f'<div class="insight-card {tone}">'
                    f'<div class="ic-body">'
                    f'<span class="ic-kind">{escape(kind)}</span>'
                    f'<span class="ic-text">{_highlight_numbers(text)}</span>'
                    f"</div></div>",
                    unsafe_allow_html=True,
                )


def show_data_page(raw_df, cleaned_df, filtered_df):
    """Render the Data page: raw, cleaned, and cleaning report."""
    raw_tab, cleaned_tab, cleaning_tab = st.tabs(
        ["Raw dataset", "Cleaned dataset", "Cleaning report"]
    )

    with raw_tab:
        raw_cols = st.columns(2)
        raw_cols[0].metric("Raw rows", f"{raw_df.shape[0]:,}")
        raw_cols[1].metric("Columns", f"{raw_df.shape[1]:,}")
        st.dataframe(raw_df.head(100), width="stretch")

    with cleaned_tab:
        cleaned_cols = st.columns(2)
        cleaned_cols[0].metric("Cleaned rows", f"{cleaned_df.shape[0]:,}")
        cleaned_cols[1].metric("Filtered rows", f"{filtered_df.shape[0]:,}")
        st.caption(
            "Sidebar filters apply to Overview, Visualizations, Analysis, and Insights — not this full cleaned preview."
        )
        st.dataframe(cleaned_df.head(100), width="stretch")
        if st.button("Save cleaned dataset"):
            saved_path = save_cleaned_dataset(cleaned_df)
            st.success(f"Cleaned dataset saved to `{saved_path}`")

    with cleaning_tab:
        show_cleaning_report(raw_df, cleaned_df, filtered_df)


NAV_PAGES = ["Overview", "Visualizations", "Analysis", "Data", "Insights"]
NAV_ICONS = ["grid-1x2-fill", "bar-chart-fill", "table", "database-fill", "lightbulb-fill"]

NAV_STYLES = {
    "container": {"padding": "0.35rem 0", "background-color": "transparent"},
    "icon": {"color": "#8991aa", "font-size": "1.05rem"},
    "nav-link": {
        "font-size": "0.96rem",
        "font-weight": "700",
        "color": "#8088a2",
        "padding": "0.78rem 0.95rem",
        "margin": "0.32rem 0",
        "border-radius": "15px",
    },
    "nav-link-selected": {
        "background-color": "#2f7d6d",
        "color": "#ffffff",
        "font-weight": "800",
        "box-shadow": "0 18px 34px -22px rgba(47, 125, 109, 0.72)",
    },
}


inject_styles()

sidebar_brand()

with st.sidebar:
    page = option_menu(
        menu_title=None,
        options=NAV_PAGES,
        icons=NAV_ICONS,
        default_index=0,
        styles=NAV_STYLES,
    )
    st.markdown("---")

raw_df = load_project_dataset()
cleaned_df = clean_dataset(raw_df) if raw_df is not None else None

if cleaned_df is None:
    page_title("Overview")
    st.error(
        f"Place `{BASE_DATASET_NAME}` inside `data/raw/` to load the dashboard."
    )
    st.info("Dashboard pages will appear after the project dataset is available.")
else:
    filtered_df = filter_dataset(cleaned_df)
    analysis_outputs = load_processed_analysis_outputs()
    processed_analysis = load_processed_financial_analysis()

    if filtered_df.empty:
        page_title(page, total_rows=len(cleaned_df))
        st.warning("No records match the selected filters.")
    else:
        base_summary = get_basic_summary(filtered_df)
        summary = build_processed_display_summary(
            analysis_outputs,
            processed_analysis,
            base_summary,
        )
        showing = f"{len(filtered_df):,} of {len(cleaned_df):,} transactions"
        page_title(page, showing=showing)

        if page == "Overview":
            show_overview(summary, filtered_df, analysis_outputs)
        elif page == "Visualizations":
            show_charts(
                filtered_df,
                analysis_outputs if summary.get("is_processed_summary") else None,
            )
        elif page == "Analysis":
            show_analysis_tables(summary, filtered_df, analysis_outputs)
        elif page == "Data":
            show_data_page(raw_df, cleaned_df, filtered_df)
        elif page == "Insights":
            show_visual_insights(filtered_df, summary)
