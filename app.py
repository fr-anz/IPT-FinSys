from html import escape
import io
import re

import pandas as pd
import streamlit as st
from streamlit_option_menu import option_menu

from src.analysis import get_basic_summary
from src.config import BASE_DATASET_NAME
from src.data_cleaning import clean_dataset
from src.data_loader import dataset_exists, load_raw_dataset, save_cleaned_dataset
from src.insights import generate_insights
from src.summary_exports import export_summary_csvs
from src.visualizations import (
    create_budget_gauge,
    create_mini_monthly_line,
    create_top_categories_bar,
    create_visualization_charts,
)


st.set_page_config(
    page_title="Financial Expense Monitoring Dashboard",
    page_icon="\U0001f4b9",
    layout="wide",
    initial_sidebar_state="auto",
)


def inject_styles():
    """Apply the dashboard visual system."""
    st.markdown(
        """
        <style>
        :root {
            --page: #f5f6f7;
            --surface: #ffffff;
            --surface-strong: #edf0ef;
            --ink: #18201d;
            --muted: #66706b;
            --line: #d9dfdc;
            --accent: #2f7d6d;
            --accent-dark: #205a50;
            --warning: #9d5d28;
            --shadow: 0 1px 2px rgba(24, 32, 29, 0.05), 0 6px 18px rgba(24, 32, 29, 0.05);
        }

        html, body, [class*="css"] {
            font-family: "Aptos", "Segoe UI", system-ui, sans-serif;
            color: var(--ink);
        }

        .stApp {
            background: #eef1f0;
        }

        .block-container {
            max-width: 100%;
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            padding-left: 2rem;
            padding-right: 2rem;
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] > div:first-child { padding-top: 1.1rem; }

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

        .app-topbar {
            position: sticky;
            top: 0;
            z-index: 1000;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            margin: 0 0 1.2rem;
            padding: 0.7rem 1rem;
            background: rgba(255, 255, 255, 0.88);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--line);
            border-radius: 10px;
            box-shadow: var(--shadow);
        }

        .brand { display: flex; align-items: center; gap: 0.65rem; }

        .brand-mark {
            width: 2.2rem;
            height: 2.2rem;
            border-radius: 8px;
            background: linear-gradient(145deg, #215f54 0%, #2f7d6d 100%);
            color: #ffffff;
            font-size: 1.15rem;
            font-weight: 800;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 8px 18px rgba(47, 125, 109, 0.35);
        }

        .brand-text { display: flex; flex-direction: column; line-height: 1.12; }
        .brand-name { color: var(--ink); font-size: 1rem; font-weight: 790; }
        .brand-sub { color: var(--muted); font-size: 0.72rem; font-weight: 640; }

        .topbar-status {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: #e2f0ec;
            border: 1px solid rgba(47, 125, 109, 0.24);
            border-radius: 999px;
            color: var(--accent-dark);
            font-size: 0.8rem;
            font-weight: 650;
            padding: 0.4rem 0.85rem;
        }

        .status-dot {
            width: 0.55rem;
            height: 0.55rem;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 0 3px rgba(47, 125, 109, 0.18);
        }

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

        .hero-panel {
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(217, 223, 220, 0.95);
            border-radius: 8px;
            padding: 1.15rem 1.4rem;
            margin-bottom: 0.5rem;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.97), rgba(237, 240, 239, 0.92)),
                repeating-linear-gradient(90deg, rgba(47, 125, 109, 0.04) 0 1px, transparent 1px 18px);
            box-shadow: var(--shadow);
        }

        .hero-kicker {
            color: var(--accent-dark);
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.04em;
            margin-bottom: 0.35rem;
            text-transform: uppercase;
        }

        .hero-title {
            color: var(--ink);
            font-size: 1.75rem;
            font-weight: 770;
            letter-spacing: 0;
            line-height: 1.12;
            margin: 0;
            max-width: 30ch;
            text-wrap: balance;
        }

        .hero-copy {
            color: var(--muted);
            font-size: 0.92rem;
            line-height: 1.55;
            margin: 0.5rem 0 0;
            max-width: 72ch;
        }

        .dataset-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            background: #e2f0ec;
            border: 1px solid rgba(47, 125, 109, 0.24);
            border-radius: 8px;
            color: var(--accent-dark);
            font-size: 0.82rem;
            font-weight: 650;
            margin-top: 1.15rem;
            padding: 0.45rem 0.8rem;
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

        .metric-card {
            min-height: 6.4rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            gap: 0.55rem;
            background: var(--surface);
            border: 1px solid rgba(217, 223, 220, 0.95);
            border-radius: 12px;
            box-shadow: var(--shadow);
            padding: 1.35rem 1.45rem;
            transition: transform 220ms ease, border-color 220ms ease, box-shadow 220ms ease;
        }

        .metric-card:hover {
            border-color: rgba(47, 125, 109, 0.34);
            box-shadow: 0 12px 30px rgba(24, 32, 29, 0.10);
            transform: translateY(-2px);
        }

        .metric-label {
            color: var(--muted);
            display: block;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            margin: 0;
            text-transform: uppercase;
        }

        .metric-value {
            color: var(--ink);
            display: block;
            font-size: 1.85rem;
            font-variant-numeric: tabular-nums;
            font-weight: 760;
            letter-spacing: 0;
            line-height: 1.05;
            margin: 0;
            overflow-wrap: anywhere;
        }

        .metric-note {
            color: var(--muted);
            display: block;
            font-size: 0.82rem;
            line-height: 1.35;
            margin-top: 0.7rem;
        }

        .metric-card--accent {
            background: linear-gradient(145deg, #215f54 0%, #2f7d6d 100%);
            border-color: rgba(47, 125, 109, 0.5);
        }

        .metric-card--accent .metric-label,
        .metric-card--accent .metric-note {
            color: rgba(255, 255, 255, 0.74);
        }

        .metric-card--accent .metric-value {
            color: #ffffff;
        }

        .metric-card--warning .metric-value {
            color: var(--warning);
        }

        .chart-title {
            color: var(--ink);
            font-size: 0.98rem;
            font-weight: 720;
            letter-spacing: 0;
            margin: 0.1rem 0 0.45rem;
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
            margin-bottom: 1.1rem;
        }

        .page-title-bar .pt-left { display: flex; flex-direction: column; gap: 0.2rem; }
        .page-title-bar .pt-kicker {
            color: var(--accent-dark);
            font-size: 0.7rem;
            font-weight: 760;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .page-title-bar .pt-title {
            color: var(--ink);
            font-size: 1.5rem;
            font-weight: 770;
            line-height: 1.1;
            margin: 0;
        }
        .page-title-bar .pt-sub { color: var(--muted); font-size: 0.86rem; }

        .pt-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 999px;
            color: var(--accent-dark);
            font-size: 0.8rem;
            font-weight: 650;
            padding: 0.45rem 0.9rem;
            box-shadow: var(--shadow);
            white-space: nowrap;
        }

        /* ---- Sidebar brand ---- */
        .sb-brand { display: flex; align-items: center; gap: 0.65rem; padding: 0 0.25rem 0.5rem; }
        .sb-brand .brand-mark { width: 2.4rem; height: 2.4rem; font-size: 1.25rem; }

        /* ---- Bento cards with embedded content ---- */
        .bento-card {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 12px;
            box-shadow: var(--shadow);
            padding: 1.1rem 1.2rem;
            height: 100%;
        }
        .bento-card .bento-head {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.35rem;
        }
        .bento-card .bento-title {
            color: var(--ink);
            font-size: 0.95rem;
            font-weight: 720;
        }
        .bento-card .bento-tag {
            color: var(--muted);
            font-size: 0.72rem;
            font-weight: 650;
            background: var(--surface-strong);
            border-radius: 999px;
            padding: 0.18rem 0.6rem;
        }
        .bento-card .bento-sub { color: var(--muted); font-size: 0.8rem; margin: 0 0 0.4rem; }

        /* Bordered containers act as bento cards */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface);
            border-radius: 12px;
            box-shadow: var(--shadow);
        }
        .bento-title { color: var(--ink); font-size: 0.95rem; font-weight: 720; }
        .bento-sub { color: var(--muted); font-size: 0.8rem; margin: 0 0 0.3rem; }

        /* ---- Visual insight cards ---- */
        .insight-card {
            display: flex;
            gap: 0.85rem;
            background: var(--surface);
            border: 1px solid var(--line);
            border-left: 4px solid var(--accent);
            border-radius: 12px;
            box-shadow: var(--shadow);
            padding: 1rem 1.1rem;
            height: 100%;
        }
        .insight-card.tone-trend { border-left-color: #4e7fa1; }
        .insight-card.tone-reco { border-left-color: #b2863f; }
        .insight-card.tone-conclusion { border-left-color: #7a6aa0; }

        .insight-card .ic-icon {
            flex: 0 0 2.4rem;
            width: 2.4rem;
            height: 2.4rem;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            background: #e2f0ec;
        }
        .insight-card.tone-trend .ic-icon { background: #e3edf3; }
        .insight-card.tone-reco .ic-icon { background: #f4ecda; }
        .insight-card.tone-conclusion .ic-icon { background: #ece8f3; }

        .insight-card .ic-body { display: flex; flex-direction: column; gap: 0.15rem; }
        .insight-card .ic-kind {
            font-size: 0.68rem;
            font-weight: 760;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            color: var(--muted);
        }
        .insight-card .ic-text { color: var(--ink); font-size: 0.9rem; line-height: 1.5; }
        .insight-card .ic-text b { color: var(--accent-dark); }

        @media (max-width: 980px) {
            .stat-grid { grid-template-columns: repeat(3, 1fr); }
        }

        @media (max-width: 760px) {
            .block-container {
                padding-left: 1rem;
                padding-right: 1rem;
            }

            .hero-panel {
                padding: 1.05rem 1.1rem;
            }

            .hero-title {
                font-size: 1.5rem;
            }

            .hero-copy {
                font-size: 0.88rem;
            }

            .metric-value {
                font-size: 1.45rem;
            }

            .section-heading {
                align-items: start;
                flex-direction: column;
            }

            .topbar-status {
                font-size: 0;
                padding: 0.45rem;
                gap: 0;
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


def metric_card(label, value, note, tone="neutral"):
    """Render a custom metric card (label + value only)."""
    st.markdown(
        f"""
        <div class="metric-card metric-card--{escape(tone)}">
            <span class="metric-label">{escape(label)}</span>
            <span class="metric-value">{escape(str(value))}</span>
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
    """Render the compact page title bar (title only)."""
    st.markdown(
        f"""
        <div class="page-title-bar">
            <div class="pt-left">
                <h1 class="pt-title">{escape(page)}</h1>
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


def show_metric_cards(summary):
    """Display the main dashboard metrics."""
    budget_summary = summary.get("budget_summary", {})
    stats = summary.get("amount_statistics", {})
    remaining_budget = budget_summary.get("remaining_budget")
    remaining_tone = "warning" if remaining_budget is not None and remaining_budget < 0 else "neutral"

    metric_rows = [
        [
            (
                "Transactions",
                format_number(summary.get("total_transactions", 0)),
                "Filtered records included in the analysis",
                "neutral",
            ),
            (
                "Total spent",
                format_php(summary.get("total_expense")),
                "Net recorded transaction amount",
                "accent",
            ),
            (
                "Average expense",
                format_php(summary.get("average_expense")),
                "Mean transaction value",
                "neutral",
            ),
            (
                "Budget used",
                f"{budget_summary.get('budget_usage_percent', 0):.1f}%",
                "Total spent compared with budget limit",
                "neutral",
            ),
        ],
        [
            ("Median", format_php(stats.get("median")), "Middle transaction value", "neutral"),
            ("Minimum", format_php(stats.get("min")), "Lowest transaction amount", "neutral"),
            ("Maximum", format_php(stats.get("max")), "Highest transaction amount", "neutral"),
            (
                "Remaining budget",
                format_php(remaining_budget),
                "Budget left after recorded spending",
                remaining_tone,
            ),
        ],
    ]

    for index, row in enumerate(metric_rows):
        if index > 0:
            st.write("")
        cols = st.columns(4, gap="large")
        for col, (label, value, note, tone) in zip(cols, row):
            with col:
                metric_card(label, value, note, tone)


def show_statistics(summary):
    """Render the full statistical summary required by the rubric."""
    stats = summary.get("amount_statistics", {})
    tiles = [
        ("Mean", format_php(stats.get("mean"))),
        ("Median", format_php(stats.get("median"))),
        ("Mode", format_php(stats.get("mode"))),
        ("Std. deviation", format_php(stats.get("standard_deviation"))),
        ("Minimum", format_php(stats.get("min"))),
        ("Maximum", format_php(stats.get("max"))),
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
            "Rows with no transaction id, unparseable date, or missing amount removed",
        ),
    ]
    report_html = "".join(
        f'<div class="insight-item"><strong>{escape(title)}.</strong> {escape(detail)}</div>'
        for title, detail in steps
    )
    st.markdown(report_html, unsafe_allow_html=True)


def load_raw_data_from_sidebar():
    """Load raw CSV from sidebar upload or project data/raw folder."""
    uploaded = st.sidebar.file_uploader(
        "Upload CSV",
        type=["csv"],
        help=f"Optional. Falls back to data/raw/{BASE_DATASET_NAME}.",
    )
    if uploaded is not None:
        st.session_state["uploaded_raw"] = uploaded.getvalue()
        return pd.read_csv(io.BytesIO(st.session_state["uploaded_raw"]))

    if "uploaded_raw" in st.session_state:
        del st.session_state["uploaded_raw"]

    if dataset_exists():
        return load_raw_dataset()
    return None


def show_analysis_tables(summary, df):
    """Display grouped analysis tables in tabs."""
    export_col, _ = st.columns([1, 3])
    with export_col:
        if st.button("Export summary CSVs", width="stretch"):
            exported_paths = export_summary_csvs(df)
            st.session_state["exported_summary_paths"] = exported_paths

    exported_paths = st.session_state.get("exported_summary_paths")
    if exported_paths:
        st.success(
            "Summary CSVs saved to `data/outputs/`: "
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
    tabs = st.tabs(
        [
            "Category totals",
            "Monthly trends",
            "Budget summary",
            "Correlations",
            "Frequencies",
        ]
    )

    with tabs[0]:
        category_totals = summary.get("category_totals", {})
        if category_totals:
            category_df = pd.DataFrame(
                category_totals.items(), columns=["Category", "Total Amount"]
            )
            st.dataframe(
                category_df,
                width='stretch',
                hide_index=True,
                column_config={
                    "Total Amount": st.column_config.NumberColumn(
                        "Total Amount", format="PHP %.2f"
                    )
                },
            )
        else:
            st.info("Category totals are unavailable for the selected data.")

    with tabs[1]:
        monthly_trends = summary.get("monthly_trends", {})
        if monthly_trends:
            monthly_df = pd.DataFrame.from_dict(monthly_trends, orient="index")
            monthly_df.index.name = "Month"
            st.dataframe(
                monthly_df.reset_index(),
                width='stretch',
                hide_index=True,
                column_config={
                    "total": st.column_config.NumberColumn("Total", format="PHP %.2f"),
                    "average": st.column_config.NumberColumn(
                        "Average", format="PHP %.2f"
                    ),
                    "transaction_count": st.column_config.NumberColumn(
                        "Transactions", format="%d"
                    ),
                },
            )
        else:
            st.info("Monthly trends are unavailable for the selected data.")

    with tabs[2]:
        budget_by_category = summary.get("budget_by_category", {})
        if budget_by_category:
            budget_df = pd.DataFrame.from_dict(budget_by_category, orient="index")
            budget_df.index.name = "Category"
            st.dataframe(
                budget_df.reset_index(),
                width='stretch',
                hide_index=True,
                column_config={
                    "total_spent": st.column_config.NumberColumn(
                        "Total Spent", format="PHP %.2f"
                    ),
                    "total_budget": st.column_config.NumberColumn(
                        "Total Budget", format="PHP %.2f"
                    ),
                    "remaining_budget": st.column_config.NumberColumn(
                        "Remaining Budget", format="PHP %.2f"
                    ),
                },
            )
        else:
            st.info("Budget summaries are unavailable for the selected data.")

    with tabs[3]:
        correlation = summary.get("correlation_analysis", {})
        matrix = correlation.get("matrix", {})
        amount_correlations = correlation.get("amount_correlations", {})
        if matrix:
            st.dataframe(
                pd.DataFrame.from_dict(matrix),
                width='stretch',
            )
            if amount_correlations:
                st.caption("Amount correlations ranked by absolute strength.")
                st.dataframe(
                    pd.DataFrame(
                        amount_correlations.items(),
                        columns=["Numeric Field", "Correlation With Amount"],
                    ),
                    width='stretch',
                    hide_index=True,
                )
        else:
            st.info("Correlation analysis needs at least two numeric columns.")

    with tabs[4]:
        frequency_distributions = summary.get("frequency_distributions", {})
        if frequency_distributions:
            selected_column = st.selectbox(
                "Frequency column",
                sorted(frequency_distributions.keys()),
            )
            frequency_df = pd.DataFrame.from_dict(
                frequency_distributions[selected_column], orient="index"
            )
            frequency_df.index.name = selected_column.replace("_", " ").title()
            st.dataframe(
                frequency_df.reset_index(),
                width='stretch',
                hide_index=True,
                column_config={
                    "count": st.column_config.NumberColumn("Count", format="%d"),
                    "percentage": st.column_config.NumberColumn(
                        "Percentage", format="%.2f%%"
                    ),
                },
            )
        else:
            st.info("Frequency distributions are unavailable for the selected data.")


def show_charts(df):
    """Display visualization charts in a two-column layout."""
    charts = create_visualization_charts(df)

    chart_items = [(title, fig) for title, fig in charts.items() if fig is not None]
    if not chart_items:
        st.info("Charts are unavailable for the selected data.")
        return

    chart_config = {"displayModeBar": False, "responsive": True}
    for index in range(0, len(chart_items), 2):
        cols = st.columns(2)
        for col, (title, fig) in zip(cols, chart_items[index : index + 2]):
            with col:
                st.markdown(
                    f'<div class="chart-title">{escape(title)}</div>',
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


def show_overview(summary, df):
    """Render the Overview page as a bento grid."""
    show_metric_cards(summary)
    st.write("")

    config = {"displayModeBar": False, "responsive": True}
    budget_summary = summary.get("budget_summary", {})
    col_gauge, col_trend, col_top = st.columns([1, 1.35, 1.2], gap="large")
    with col_gauge:
        bento_chart(
            "Budget usage",
            "Spent vs total budget",
            create_budget_gauge(budget_summary.get("budget_usage_percent")),
            config,
        )
    with col_trend:
        bento_chart(
            "Monthly spending",
            "Total recorded amount per month",
            create_mini_monthly_line(df),
            config,
        )
    with col_top:
        bento_chart(
            "Top categories",
            "Highest spending categories",
            create_top_categories_bar(df),
            config,
        )

    section_heading(
        "Statistical summary",
        "Mean, median, mode, spread, and range of transaction amounts.",
    )
    show_statistics(summary)


INSIGHT_STYLE = {
    "Finding": ("", "\U0001f50d", "Finding"),
    "Trend": ("tone-trend", "\U0001f4c8", "Trend"),
    "Recommendation": ("tone-reco", "\U0001f4a1", "Recommendation"),
    "Conclusion": ("tone-conclusion", "\U0001f3c1", "Conclusion"),
}


def _highlight_numbers(text):
    """Bold peso amounts and percentages inside escaped insight text."""
    safe = escape(text)
    safe = re.sub(r"(PHP\s-?[\d,]+\.\d{2})", r"<b>\1</b>", safe)
    safe = re.sub(r"(\d+\.\d+%)", r"<b>\1</b>", safe)
    return safe


def show_visual_insights(df):
    """Render insights as visual cards plus supporting charts."""
    summary = get_basic_summary(df)
    config = {"displayModeBar": False, "responsive": True}

    col_a, col_b = st.columns(2)
    with col_a:
        bento_chart(
            "Budget usage",
            "How much of the budget is consumed",
            create_budget_gauge(summary.get("budget_summary", {}).get("budget_usage_percent")),
            config,
        )
    with col_b:
        bento_chart(
            "Where the money goes",
            "Top spending categories",
            create_top_categories_bar(df),
            config,
        )

    section_heading(
        "Findings, trends & recommendations",
        "Interpreted automatically from the current filtered data.",
    )

    cards = []
    for item in generate_insights(df):
        prefix, sep, rest = item.partition(":")
        if sep and prefix.strip() in INSIGHT_STYLE:
            tone, icon, kind = INSIGHT_STYLE[prefix.strip()]
            text = rest.strip()
        else:
            tone, icon, kind = "", "\U0001f4cc", "Insight"
            text = item
        cards.append((tone, icon, kind, text))

    for index in range(0, len(cards), 2):
        cols = st.columns(2)
        for col, (tone, icon, kind, text) in zip(cols, cards[index : index + 2]):
            with col:
                st.markdown(
                    f'<div class="insight-card {tone}">'
                    f'<div class="ic-icon">{icon}</div>'
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
    "container": {"padding": "0.2rem 0", "background-color": "transparent"},
    "icon": {"color": "#66706b", "font-size": "0.95rem"},
    "nav-link": {
        "font-size": "0.92rem",
        "font-weight": "650",
        "color": "#3a443f",
        "padding": "0.55rem 0.8rem",
        "margin": "0.15rem 0",
        "border-radius": "8px",
    },
    "nav-link-selected": {
        "background-color": "#2f7d6d",
        "color": "#ffffff",
        "font-weight": "700",
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

raw_df = load_raw_data_from_sidebar()
cleaned_df = clean_dataset(raw_df) if raw_df is not None else None

if cleaned_df is None:
    page_title("Overview")
    st.error(
        f"Upload a CSV in the sidebar or place `{BASE_DATASET_NAME}` inside `data/raw/`."
    )
    st.info("Dashboard pages will appear after a valid dataset is loaded.")
else:
    filtered_df = filter_dataset(cleaned_df)

    if filtered_df.empty:
        page_title(page, total_rows=len(cleaned_df))
        st.warning("No records match the selected filters.")
    else:
        summary = get_basic_summary(filtered_df)
        showing = f"{len(filtered_df):,} of {len(cleaned_df):,} transactions"
        page_title(page, showing=showing)

        if page == "Overview":
            show_overview(summary, filtered_df)
        elif page == "Visualizations":
            show_charts(filtered_df)
        elif page == "Analysis":
            show_analysis_tables(summary, filtered_df)
        elif page == "Data":
            show_data_page(raw_df, cleaned_df, filtered_df)
        elif page == "Insights":
            show_visual_insights(filtered_df)

