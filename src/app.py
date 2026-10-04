"""
F&B Item Sales Dashboard
Styled to match the Canobie Lake Park Inventory Dashboard (Next.js version).
Supports both local SQLite and cloud Supabase PostgreSQL.
"""

import sqlite3
import os
import re
import io
from datetime import datetime, timedelta
from pathlib import Path
import pickle

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import database abstraction layer
from db import is_cloud_mode, read_sql, execute_sql, save_dataframe, delete_by_dates, table_exists, db_exists, get_db_info

# =============================================================================
# PAGE CONFIG & STYLING
# =============================================================================

st.set_page_config(
    page_title="Canobie Lake Park - F&B Sales",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS matching the inventory dashboard exactly
st.markdown("""
<style>
    /* Import Geist-like font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Main background - exact match */
    .stApp {
        background-color: #0a0a0a;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Remove default Streamlit padding at top */
    .block-container {
        padding-top: 0 !important;
        max-width: 100% !important;
    }

    /* Header */
    header[data-testid="stHeader"] {
        background-color: #0a0a0a;
        border-bottom: 1px solid #1f1f1f;
    }

    /* Hide the default Streamlit header */
    [data-testid="stHeader"] {
        display: none;
    }

    /* All text defaults - LARGER base size */
    .stApp, .stApp p, .stApp span, .stApp div {
        color: #ededed;
        font-size: 15px;
    }

    /* Headers - BOLDER and LARGER */
    h1 {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 28px !important;
    }

    h2 {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 22px !important;
    }

    h3, h4 {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 18px !important;
    }

    /* Tabs - filled active state like inventory dashboard */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: transparent;
        border-bottom: none;
        padding: 0;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #9ca3af;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        font-size: 15px;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #ffffff;
        background-color: #1f2937;
    }

    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: #ffffff !important;
        border: none !important;
    }

    /* Card styling - minimal, no border */
    .card {
        padding: 0;
        margin-bottom: 24px;
    }

    .card-title {
        color: #9ca3af;
        font-size: 14px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 12px;
    }

    /* KPI Card - single accent color, clean style */
    .kpi-card {
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 8px;
        padding: 20px 24px;
    }

    .kpi-label {
        font-size: 13px !important;
        font-weight: 500 !important;
        color: #9ca3af !important;
        margin-bottom: 8px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }

    .kpi-value {
        color: #ffffff !important;
        font-size: 32px !important;
        font-weight: 600 !important;
        line-height: 1.2 !important;
    }

    .kpi-subtitle {
        color: #6b7280 !important;
        font-size: 13px !important;
        margin-top: 6px !important;
    }

    /* Section divider */
    .section-divider {
        border-top: 1px solid #1f2937;
        margin: 32px 0;
    }

    /* Alternating row colors for tables */
    [data-testid="stDataFrame"] tbody tr:nth-child(even) {
        background-color: rgba(31, 41, 55, 0.3) !important;
    }
    [data-testid="stDataFrame"] tbody tr:nth-child(odd) {
        background-color: rgba(17, 24, 39, 0.3) !important;
    }

    /* Section header */
    .section-header {
        margin-bottom: 28px;
    }

    .section-title {
        color: #ffffff;
        font-size: 22px;
        font-weight: 600;
        margin: 0;
    }

    .section-subtitle {
        color: #9ca3af;
        font-size: 15px;
        margin-top: 6px;
    }

    /* Dashboard header bar - matching inventory dashboard */
    .dash-header {
        background-color: #0a0a0a;
        border-bottom: 1px solid #1f2937;
        padding: 16px 0 12px 0;
        margin: 0 0 0 0;
    }

    .dash-title {
        color: #ffffff !important;
        font-size: 24px !important;
        font-weight: 700 !important;
        margin: 0 !important;
        line-height: 1.3 !important;
    }

    .dash-subtitle {
        color: #9ca3af !important;
        font-size: 16px !important;
        margin-top: 4px !important;
    }

    .badge {
        background-color: rgba(59, 130, 246, 0.2);
        color: #60a5fa;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 14px;
        font-weight: 500;
        margin-left: 14px;
        vertical-align: middle;
    }

    /* Selectbox - LARGER */
    .stSelectbox > div > div {
        background-color: #111827;
        border-color: #374151;
        border-radius: 8px;
        font-size: 15px;
    }

    .stSelectbox label {
        color: #9ca3af !important;
        font-size: 14px;
    }

    /* DataFrame - better styling */
    [data-testid="stDataFrame"] {
        border-radius: 12px;
        overflow: hidden;
        font-size: 14px;
    }

    /* Buttons - LARGER */
    .stButton > button {
        background-color: #2563eb;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 500;
        font-size: 15px;
    }

    .stButton > button:hover {
        background-color: #1d4ed8;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background-color: rgba(31, 41, 55, 0.5);
        border: 2px dashed #374151;
        border-radius: 12px;
        padding: 24px;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #111827;
        border-radius: 8px;
        color: #e5e7eb !important;
        font-weight: 500;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Progress */
    .stProgress > div > div > div {
        background-color: #2563eb;
    }

    /* Multiselect - LARGER */
    .stMultiSelect > div > div {
        background-color: #111827;
        border-color: #374151;
        font-size: 15px;
    }

    /* Radio - styled as toggle */
    .stRadio > div {
        background-color: #1f2937;
        border-radius: 8px;
        padding: 4px;
        display: inline-flex;
        gap: 4px;
    }
    .stRadio label {
        color: #9ca3af !important;
        font-size: 14px;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .stRadio label:has(input:checked) {
        background-color: #2563eb;
        color: #ffffff !important;
    }
    .stRadio label span {
        color: inherit !important;
    }
    .stRadio input {
        display: none;
    }

    /* Slider */
    .stSlider label {
        color: #9ca3af !important;
    }

    /* Download button - LARGER */
    .stDownloadButton > button {
        background-color: #065f46;
        border: none;
        padding: 10px 20px;
        font-size: 15px;
    }

    .stDownloadButton > button:hover {
        background-color: #047857;
    }

    /* Warning/Info */
    .stAlert {
        background-color: #1f2937;
        border: 1px solid #374151;
        border-radius: 8px;
        font-size: 15px;
    }

    /* Hide metric default styling */
    [data-testid="metric-container"] {
        display: none;
    }

    /* Summary bubble stats - matching inventory dashboard */
    .stat-bubble {
        background: linear-gradient(to bottom right, rgba(31, 41, 55, 0.5), rgba(17, 24, 39, 0.5));
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 20px;
    }

    .stat-bubble-label {
        color: #9ca3af;
        font-size: 14px;
        margin-bottom: 6px;
    }

    .stat-bubble-value {
        color: #ffffff;
        font-size: 28px;
        font-weight: 700;
    }

    /* Confidential watermark footer */
    .watermark {
        position: fixed;
        bottom: 8px;
        left: 0;
        right: 0;
        text-align: center;
        color: #ef4444;
        font-size: 11px;
        font-weight: 500;
        letter-spacing: 0.05em;
        pointer-events: none;
        z-index: 9999;
    }
</style>
<div class="watermark">Canobie Lake Park Confidential</div>
""", unsafe_allow_html=True)

# =============================================================================
# PATHS & DATABASE
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "fb_sales.db"
MODEL_PATH = PROJECT_ROOT / "forecast_model.pkl"
SALES_FOLDER = PROJECT_ROOT / "data" / "sales"

# Chart colors
COLORS = {
    'blue': '#3b82f6',
    'green': '#22c55e',
    'yellow': '#eab308',
    'red': '#ef4444',
    'purple': '#a855f7',
    'gray': '#6b7280',
    'teal': '#14b8a6',
    'orange': '#f97316'
}

# Category bar colors (matching inventory dashboard)
CATEGORY_COLORS = ['#3b82f6', '#22c55e', '#eab308', '#ef4444', '#a855f7', '#14b8a6']

# =============================================================================
# DATA LOADING
# =============================================================================

@st.cache_data(ttl=60)
def load_sales_data():
    """Load sales data with categories. Works with both SQLite and PostgreSQL."""
    # Check if database exists (works for both local and cloud)
    if not db_exists():
        return None

    try:
        df = read_sql("""
            SELECT s.*,
                   COALESCE(c.category_name, 'Uncategorized') as category,
                   COALESCE(c.subcategory_name, 'Unknown') as subcategory
            FROM sales_featured s
            LEFT JOIN item_categories c ON s.plu = c.PLU
        """)
    except Exception as e:
        # If item_categories table doesn't exist, load without it
        try:
            df = read_sql("SELECT *, 'Uncategorized' as category, 'Unknown' as subcategory FROM sales_featured")
        except:
            return None

    df['date'] = pd.to_datetime(df['date'])

    # TEMPORARY: Exclude 2023 and 2024 data (remove this line to restore)
    df = df[df['year'] >= 2025]

    return df


@st.cache_resource
def load_model():
    """Load trained forecasting model."""
    if not MODEL_PATH.exists():
        return None
    with open(MODEL_PATH, 'rb') as f:
        return pickle.load(f)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def filter_ytd_same_dow(df, date_col='date'):
    """
    Filter dataframe to YTD with day-of-week alignment across years.
    For 2025 vs 2026: adds 1 day to 2025 dates since 2025 wasn't a leap year.
    This ensures Saturday Aug 22, 2026 compares to Saturday Aug 23, 2025.
    """
    today = datetime.now()
    current_year = today.year

    df = df.copy()

    # Calculate day offset for each year relative to current year
    # Non-leap year = +1 day shift, leap year = +2 day shift
    def get_day_offset(year):
        """Days to add to align day-of-week with current year."""
        offset = 0
        for y in range(year, current_year):
            # Leap year has 366 days (+2 dow shift), regular has 365 (+1 dow shift)
            if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
                offset += 2
            else:
                offset += 1
        return offset % 7  # Only care about day of week (0-6)

    # For each year, calculate the equivalent cutoff date
    # Current year: use today's date
    # Past years: use today's date + offset days
    results = []
    for year in df['year'].unique():
        year_df = df[df['year'] == year]
        if year == current_year:
            # Current year: include up to today
            year_filtered = year_df[year_df[date_col].dt.date <= today.date()]
        else:
            # Past year: include up to today + offset (to match day of week)
            offset = get_day_offset(int(year))
            cutoff = today + pd.Timedelta(days=offset)
            year_filtered = year_df[
                (year_df[date_col].dt.month < cutoff.month) |
                ((year_df[date_col].dt.month == cutoff.month) &
                 (year_df[date_col].dt.day <= cutoff.day))
            ]
        results.append(year_filtered)

    return pd.concat(results, ignore_index=True) if results else df.iloc[0:0]


def format_currency(value):
    """Format as currency."""
    if abs(value) >= 1000000:
        return f"${value/1000000:.1f}M"
    elif abs(value) >= 1000:
        return f"${value:,.0f}"
    return f"${value:.0f}"


def format_number(value):
    """Format with commas."""
    return f"{value:,.0f}"


def render_kpi_card(label, value, subtitle=""):
    """Render a clean KPI card."""
    st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {f'<div class="kpi-subtitle">{subtitle}</div>' if subtitle else ''}
        </div>
    """, unsafe_allow_html=True)


def render_section_divider():
    """Render a subtle section divider."""
    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)


def render_card_header(title):
    """Render a card header."""
    st.markdown(f'<div class="card-title">{title}</div>', unsafe_allow_html=True)


def get_chart_layout(height=350):
    """Get chart layout matching inventory dashboard."""
    return dict(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#9ca3af', family='Inter, -apple-system, sans-serif', size=13),
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(size=13, color='#9ca3af')
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='#1f2937',
            zeroline=False,
            tickfont=dict(size=13, color='#9ca3af')
        ),
        hoverlabel=dict(
            bgcolor='#1f2937',
            font_size=13,
            font_family='Inter'
        )
    )


def style_dataframe_with_changes(df, money_cols=None, pct_cols=None, int_cols=None):
    """
    Apply conditional formatting to Change columns and number formatting.
    Green for positive, red for negative values in Change columns.
    """
    if money_cols is None:
        money_cols = []
    if pct_cols is None:
        pct_cols = []
    if int_cols is None:
        int_cols = []

    def color_negative_red(val):
        if pd.isna(val):
            return ''
        try:
            if val > 0:
                return 'color: #22c55e'  # Green
            elif val < 0:
                return 'color: #ef4444'  # Red
            return ''
        except:
            return ''

    # Find change columns
    change_cols = [col for col in df.columns if 'Change' in str(col)]

    # Build format dict
    format_dict = {}
    for col in money_cols:
        if col in df.columns:
            format_dict[col] = '${:,.0f}'
    for col in pct_cols:
        if col in df.columns:
            format_dict[col] = '{:.1f}%'
    for col in int_cols:
        if col in df.columns:
            format_dict[col] = '{:,.0f}'

    # Apply styling
    styled = df.style

    if format_dict:
        styled = styled.format(format_dict)

    if change_cols:
        # Use map instead of applymap (applymap is deprecated in pandas 2.1+)
        try:
            styled = styled.map(color_negative_red, subset=[c for c in change_cols if c in df.columns])
        except AttributeError:
            # Fallback for older pandas
            styled = styled.applymap(color_negative_red, subset=[c for c in change_cols if c in df.columns])

    return styled


# =============================================================================
# TAB 1: SALES OVERVIEW
# =============================================================================

def render_sales_overview(df):
    """Render the Sales Overview tab."""

    # Section header with year selector
    col1, col2 = st.columns([4, 1])

    with col1:
        st.markdown("""
            <div class="section-header">
                <div class="section-title">Sales Overview</div>
                <div class="section-subtitle" id="sales-subtitle"></div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        years = sorted(df['year'].unique())
        selected_year = st.selectbox("Year", years, index=len(years)-1, key="overview_year", label_visibility="collapsed")

    # Update subtitle via markdown
    st.markdown(f'<script>document.getElementById("sales-subtitle").innerText="{selected_year} Sales Data";</script>', unsafe_allow_html=True)

    # Filter data by year
    filtered_df = df[df['year'] == selected_year]

    # Calculate operating days: only count days in operating season (May-Nov) with real revenue
    # Filter to operating season months (5-11) and calculate daily totals
    season_df = filtered_df[filtered_df['month'].isin([5, 6, 7, 8, 9, 10, 11])]
    daily_revenue = season_df.groupby(season_df['date'].dt.date)['total_price'].sum()
    # Only count days where daily revenue > $1000 (real operating days, not minimal off-day sales)
    operating_days = (daily_revenue > 1000).sum()

    # For KPIs, only include items with actual positive sales (but from all data, not just season)
    paid_items = filtered_df[filtered_df['total_price'] > 0]

    # KPIs from paid items only
    total_revenue = paid_items['total_price'].sum()
    total_qty = paid_items[paid_items['total_qty'] > 0]['total_qty'].sum()
    unique_items = paid_items['plu'].nunique()

    # ===================
    # KPI CARDS
    # ===================
    cols = st.columns(4)

    with cols[0]:
        render_kpi_card("Total Sales", format_currency(total_revenue))

    with cols[1]:
        render_kpi_card("Units Sold", format_number(total_qty))

    with cols[2]:
        avg_daily = total_revenue / operating_days if operating_days > 0 else 0
        render_kpi_card("Daily Average", format_currency(avg_daily))

    with cols[3]:
        render_kpi_card("Operating Days", format_number(operating_days))

    # ===================
    # YoY COMPARISON (vs Last Year)
    # ===================
    last_year = selected_year - 1
    if last_year in df['year'].values:
        last_year_df = df[df['year'] == last_year]
        last_year_paid = last_year_df[last_year_df['total_price'] > 0]

        # Get comparable YTD data for last year
        today = datetime.now()
        # Filter last year to same point in season (by month/day)
        last_year_ytd = last_year_paid[
            (last_year_paid['date'].dt.month < today.month) |
            ((last_year_paid['date'].dt.month == today.month) &
             (last_year_paid['date'].dt.day <= today.day))
        ]

        # Also filter current year to YTD
        current_ytd = paid_items[
            (paid_items['date'].dt.month < today.month) |
            ((paid_items['date'].dt.month == today.month) &
             (paid_items['date'].dt.day <= today.day))
        ]

        ly_revenue = last_year_ytd['total_price'].sum()
        cy_revenue = current_ytd['total_price'].sum()
        ly_qty = last_year_ytd[last_year_ytd['total_qty'] > 0]['total_qty'].sum()
        cy_qty = current_ytd[current_ytd['total_qty'] > 0]['total_qty'].sum()

        if ly_revenue > 0:
            sales_change_pct = ((cy_revenue - ly_revenue) / ly_revenue) * 100
            sales_change_sign = "+" if sales_change_pct >= 0 else ""
            sales_change_color = "#22c55e" if sales_change_pct >= 0 else "#ef4444"
        else:
            sales_change_pct = 0
            sales_change_sign = ""
            sales_change_color = "#9ca3af"

        if ly_qty > 0:
            qty_change_pct = ((cy_qty - ly_qty) / ly_qty) * 100
            qty_change_sign = "+" if qty_change_pct >= 0 else ""
            qty_change_color = "#22c55e" if qty_change_pct >= 0 else "#ef4444"
        else:
            qty_change_pct = 0
            qty_change_sign = ""
            qty_change_color = "#9ca3af"

        st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style="display: flex; gap: 24px; flex-wrap: wrap;">
                <div style="color: #9ca3af; font-size: 14px;">
                    <span style="color: #6b7280;">YTD vs {last_year}:</span>
                    <span style="color: {sales_change_color}; font-weight: 600; margin-left: 8px;">
                        {sales_change_sign}{sales_change_pct:.1f}% Sales
                    </span>
                    <span style="color: {qty_change_color}; font-weight: 600; margin-left: 16px;">
                        {qty_change_sign}{qty_change_pct:.1f}% Units
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # ===================
    # THIS WEEK VS LAST WEEK
    # ===================
    today = datetime.now()
    # Get this week's data (Sunday to today)
    start_of_week = today - timedelta(days=today.weekday() + 1)  # Last Sunday
    if start_of_week.weekday() != 6:  # Adjust if not Sunday
        start_of_week = today - timedelta(days=(today.weekday() + 1) % 7)

    this_week_df = paid_items[
        (paid_items['date'].dt.date >= start_of_week.date()) &
        (paid_items['date'].dt.date <= today.date())
    ]

    # Get last week's data (full week, same days)
    days_into_week = (today - start_of_week).days + 1
    last_week_start = start_of_week - timedelta(days=7)
    last_week_end = last_week_start + timedelta(days=days_into_week - 1)

    last_week_df = paid_items[
        (paid_items['date'].dt.date >= last_week_start.date()) &
        (paid_items['date'].dt.date <= last_week_end.date())
    ]

    this_week_sales = this_week_df['total_price'].sum()
    last_week_sales = last_week_df['total_price'].sum()

    if last_week_sales > 0 and this_week_sales > 0:
        week_change_pct = ((this_week_sales - last_week_sales) / last_week_sales) * 100
        week_change_sign = "+" if week_change_pct >= 0 else ""
        week_change_color = "#22c55e" if week_change_pct >= 0 else "#ef4444"

        st.markdown(f"""
            <div style="color: #9ca3af; font-size: 14px; margin-top: 4px;">
                <span style="color: #6b7280;">This Week vs Last:</span>
                <span style="color: {week_change_color}; font-weight: 600; margin-left: 8px;">
                    {week_change_sign}{week_change_pct:.1f}%
                </span>
                <span style="color: #6b7280; margin-left: 8px;">
                    (${this_week_sales:,.0f} vs ${last_week_sales:,.0f})
                </span>
            </div>
        """, unsafe_allow_html=True)

    render_section_divider()

    # ===================
    # CHARTS ROW 1 (using paid_items only)
    # ===================
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        render_card_header("Sales by Category")

        # Filter out categories with no sales
        cat_revenue = paid_items.groupby('category')['total_price'].sum()
        cat_revenue = cat_revenue[cat_revenue > 0].sort_values(ascending=True)

        # Use bright, visible colors
        bar_colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

        fig = go.Figure(go.Bar(
            x=cat_revenue.values,
            y=cat_revenue.index,
            orientation='h',
            marker_color=bar_colors[:len(cat_revenue)],
            text=[format_currency(v) for v in cat_revenue.values],
            textposition='auto',
            textfont=dict(color='white', size=13),
            hovertemplate='%{y}: $%{x:,.0f}<extra></extra>'
        ))

        layout = get_chart_layout(300)
        layout['yaxis']['showgrid'] = False
        layout['yaxis']['tickfont'] = dict(size=13, color='#e5e7eb')
        layout['margin'] = dict(l=10, r=60, t=10, b=10)
        fig.update_layout(**layout)

        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        render_card_header("Top 10 Sellers")

        top_items = paid_items.groupby('plu_name')['total_price'].sum().nlargest(10).sort_values()

        fig = go.Figure(go.Bar(
            x=top_items.values,
            y=top_items.index,
            orientation='h',
            marker_color=COLORS['green'],
            text=[format_currency(v) for v in top_items.values],
            textposition='auto',
            textfont=dict(color='white', size=12),
            hovertemplate='%{y}: $%{x:,.0f}<extra></extra>'
        ))

        layout = get_chart_layout(300)
        layout['yaxis']['showgrid'] = False
        layout['yaxis']['tickfont'] = dict(size=10, color='#e5e7eb')
        layout['margin'] = dict(l=10, r=50, t=10, b=10)
        fig.update_layout(**layout)

        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ===================
    # SUBCATEGORY CHART (Full Width)
    # ===================
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Sales by Subcategory")

    subcat_revenue = paid_items.groupby('subcategory')['total_price'].sum()
    subcat_revenue = subcat_revenue[subcat_revenue > 0].nlargest(12).sort_values(ascending=False)

    fig = go.Figure(go.Bar(
        x=subcat_revenue.index,
        y=subcat_revenue.values,
        marker_color=COLORS['blue'],
        hovertemplate='%{x}: $%{y:,.0f}<extra></extra>'
    ))

    layout = get_chart_layout(300)
    layout['xaxis']['tickangle'] = -45
    layout['xaxis']['tickfont'] = dict(size=11, color='#e5e7eb')
    layout['margin'] = dict(l=50, r=10, t=20, b=100)
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ===================
    # DAY OF WEEK BREAKDOWN
    # ===================
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Average Sales by Day of Week")

    # First, get daily totals and filter to only operating days (>$10k)
    daily_totals = paid_items.groupby([paid_items['date'].dt.date, 'day_of_week'])['total_price'].sum().reset_index()
    daily_totals.columns = ['date', 'day_of_week', 'daily_sales']
    operating_days_only = daily_totals[daily_totals['daily_sales'] > 10000]

    # Calculate average sales by day of week (only from operating days)
    dow_data = operating_days_only.groupby('day_of_week').agg({
        'daily_sales': ['sum', 'count']
    }).reset_index()
    dow_data.columns = ['day', 'total_sales', 'num_days']
    dow_data['avg_sales'] = dow_data['total_sales'] / dow_data['num_days']

    # Order days properly
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    dow_data['day'] = pd.Categorical(dow_data['day'], categories=day_order, ordered=True)
    dow_data = dow_data.sort_values('day')

    # Find the best day
    best_day = dow_data.loc[dow_data['avg_sales'].idxmax(), 'day']

    # Color bars - highlight weekend and best day
    bar_colors = []
    for day in dow_data['day']:
        if day == best_day:
            bar_colors.append('#22c55e')  # Green for best day
        elif day in ['Saturday', 'Sunday']:
            bar_colors.append('#3b82f6')  # Blue for weekend
        else:
            bar_colors.append('#6b7280')  # Gray for weekdays

    fig = go.Figure(go.Bar(
        x=dow_data['day'],
        y=dow_data['avg_sales'],
        marker_color=bar_colors,
        text=[f"${v:,.0f}" for v in dow_data['avg_sales']],
        textposition='outside',
        textfont=dict(color='#9ca3af', size=11),
        hovertemplate='%{x}: $%{y:,.0f} avg<extra></extra>'
    ))

    layout = get_chart_layout(250)
    layout['xaxis']['tickfont'] = dict(size=11, color='#e5e7eb')
    layout['margin'] = dict(l=10, r=10, t=10, b=40)
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Best day: {best_day}")
    st.markdown('</div>', unsafe_allow_html=True)

    # ===================
    # DAILY TREND WITH 7-DAY MA (May-November only, days with sales > $0)
    # ===================
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Daily Sales Trend")

    # Filter to May-November (months 5-11)
    season_data = paid_items[paid_items['date'].dt.month.isin([5, 6, 7, 8, 9, 10, 11])]

    daily = season_data.groupby(season_data['date'].dt.date).agg({
        'total_price': 'sum'
    }).reset_index()
    daily.columns = ['date', 'revenue']
    daily = daily[daily['revenue'] > 0].sort_values('date')

    # 7-day moving average
    daily['ma_7'] = daily['revenue'].rolling(window=7, min_periods=1).mean()

    fig = go.Figure()

    # Daily line
    fig.add_trace(go.Scatter(
        x=daily['date'],
        y=daily['revenue'],
        mode='lines',
        name='Daily',
        line=dict(color=COLORS['blue'], width=1.5),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)',
        hovertemplate='Daily: $%{y:,.0f}<extra></extra>'
    ))

    # 7-day MA
    fig.add_trace(go.Scatter(
        x=daily['date'],
        y=daily['ma_7'],
        mode='lines',
        name='7-Day Avg',
        line=dict(color=COLORS['yellow'], width=2.5),
        hovertemplate='7-Day Avg: $%{y:,.0f}<extra></extra>'
    ))

    layout = get_chart_layout(300)
    layout['hovermode'] = 'x unified'
    layout['legend'] = dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
        xanchor='right',
        x=1,
        font=dict(size=13, color='#e5e7eb')
    )
    layout['margin'] = dict(l=10, r=10, t=40, b=10)
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# TAB 2: COMPARISON
# =============================================================================

def render_comparison(df):
    """Render comparison tab - compare items, categories, or subcategories across time."""

    st.markdown("""
        <div class="section-header">
            <div class="section-title">Compare Performance</div>
            <div class="section-subtitle">Analyze items, categories, or subcategories across time periods</div>
        </div>
    """, unsafe_allow_html=True)

    # Get current date for YTD
    today = datetime.now()
    current_month = today.month
    current_day = today.day

    years = sorted(df['year'].dropna().unique())
    categories = sorted([c for c in df['category'].unique() if c is not None and pd.notna(c)])
    subcategories = sorted([s for s in df['subcategory'].unique() if s is not None and pd.notna(s)])
    items = sorted([i for i in df['plu_name'].unique() if i is not None and pd.notna(i)])

    # Row 1: Filter controls
    col1, col2, col3, col4 = st.columns([1.2, 1.5, 1.5, 1])

    with col1:
        compare_by = st.selectbox("Compare By", ["Category", "Subcategory", "Item"], key="comp_by")

    with col2:
        if compare_by == "Category":
            # Default to main categories
            default_cats = [c for c in ["Beverage", "Alc Beverage", "Ice Cream", "Food"] if c in categories]
            selected_items = st.multiselect("Select Categories", categories, default=default_cats if default_cats else categories[:3], key="comp_cats")
        elif compare_by == "Subcategory":
            selected_items = st.multiselect("Select Subcategories", subcategories, default=subcategories[:3] if len(subcategories) >= 3 else subcategories, key="comp_subcats")
        else:
            # For items, show a searchable dropdown
            selected_items = st.multiselect("Select Items", items, default=[], key="comp_items", placeholder="Search items...")

    with col3:
        date_range = st.selectbox("Date Range", ["Year to Date", "Full Season", "Last 7 Days", "Last 30 Days", "This Month", "Last Weekend", "Custom Range"], key="comp_daterange")

    with col4:
        metric = st.selectbox("Metric", ["Sales ($)", "Units Sold"], key="comp_metric")

    # Row 2: Year selection and custom dates
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1])

    with col1:
        selected_years = st.multiselect("Years to Compare", [str(y) for y in years], default=[str(y) for y in years], key="comp_years")

    # Calculate preset date ranges
    if date_range == "Last 7 Days":
        end_date = today.date()
        start_date = (today - timedelta(days=7)).date()
    elif date_range == "Last 30 Days":
        end_date = today.date()
        start_date = (today - timedelta(days=30)).date()
    elif date_range == "This Month":
        start_date = today.replace(day=1).date()
        end_date = today.date()
    elif date_range == "Last Weekend":
        # Find last Saturday and Sunday
        days_since_sunday = today.weekday() + 1  # Monday=0, so Sunday was (weekday+1) days ago
        if days_since_sunday == 7:  # Today is Sunday
            days_since_sunday = 0
        last_sunday = today - timedelta(days=days_since_sunday)
        last_saturday = last_sunday - timedelta(days=1)
        start_date = last_saturday.date()
        end_date = last_sunday.date()
    elif date_range == "Custom Range":
        with col2:
            start_date = st.date_input("Start", value=df['date'].min().date(), key="comp_start")
        with col3:
            end_date = st.date_input("End", value=df['date'].max().date(), key="comp_end")
    else:
        start_date = None
        end_date = None

    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

    # Validate selections
    if not selected_items:
        st.info(f"Select at least one {compare_by.lower()} to compare.")
        return

    if not selected_years:
        st.info("Select at least one year.")
        return

    # Filter data
    year_list = [int(y) for y in selected_years]
    filtered_df = df[df['year'].isin(year_list)]

    # Apply date range filter
    if date_range == "Year to Date":
        # Filter to YTD by week number and day of week for apples-to-apples comparison
        filtered_df = filter_ytd_same_dow(filtered_df)
    elif date_range in ["Last 7 Days", "Last 30 Days", "This Month", "Last Weekend", "Custom Range"]:
        # Use the calculated start_date and end_date
        filtered_df = filtered_df[
            (filtered_df['date'].dt.date >= start_date) &
            (filtered_df['date'].dt.date <= end_date)
        ]

    # Filter by selected items
    if compare_by == "Category":
        filtered_df = filtered_df[filtered_df['category'].isin(selected_items)]
        group_col = 'category'
    elif compare_by == "Subcategory":
        filtered_df = filtered_df[filtered_df['subcategory'].isin(selected_items)]
        group_col = 'subcategory'
    else:
        filtered_df = filtered_df[filtered_df['plu_name'].isin(selected_items)]
        group_col = 'plu_name'

    # Apply attendance adjustment to prior years (if enabled by admin)
    filtered_df = apply_attendance_adjustment(filtered_df, value_cols=['total_price', 'total_qty'])

    # Determine metric column
    metric_col = 'total_price' if metric == "Sales ($)" else 'total_qty'
    metric_label = "Sales" if metric == "Sales ($)" else "Units"

    # Aggregate data
    comparison_data = filtered_df.groupby([group_col, 'year'])[metric_col].sum().reset_index()
    comparison_data.columns = [compare_by, 'Year', metric_label]

    # Summary KPIs
    st.markdown("<div style='height: 8px'></div>", unsafe_allow_html=True)

    # Create summary by year
    year_totals = comparison_data.groupby('Year')[metric_label].sum()
    year_list_sorted = sorted(year_totals.keys())

    # Show year comparison KPIs if exactly 2 years
    if len(year_list_sorted) == 2:
        year1, year2 = year_list_sorted
        val1, val2 = year_totals[year1], year_totals[year2]
        change_val = val2 - val1
        change_pct = ((val2 - val1) / val1 * 100) if val1 > 0 else 0
        change_sign = "+" if change_val >= 0 else ""
        change_color = "#22c55e" if change_val >= 0 else "#ef4444"

        kpi_cols = st.columns(4)

        with kpi_cols[0]:
            if metric == "Sales ($)":
                formatted_val = f"${val1:,.0f}"
            else:
                formatted_val = f"{int(val1):,}"
            render_kpi_card(f"{int(year1)} {metric_label}", formatted_val)

        with kpi_cols[1]:
            if metric == "Sales ($)":
                formatted_val = f"${val2:,.0f}"
            else:
                formatted_val = f"{int(val2):,}"
            render_kpi_card(f"{int(year2)} {metric_label}", formatted_val)

        with kpi_cols[2]:
            if metric == "Sales ($)":
                change_formatted = f"{change_sign}${change_val:,.0f}"
            else:
                change_formatted = f"{change_sign}{int(change_val):,}"
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">$ Change</div>
                    <div style="color: {change_color}; font-size: 32px; font-weight: 600;">{change_formatted}</div>
                </div>
            """, unsafe_allow_html=True)

        with kpi_cols[3]:
            st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label">% Change</div>
                    <div style="color: {change_color}; font-size: 32px; font-weight: 600;">{change_sign}{change_pct:.1f}%</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        # Single year or more than 2 years - show totals
        kpi_cols = st.columns(len(year_totals))
        for idx, (year, total) in enumerate(year_totals.items()):
            with kpi_cols[idx]:
                if metric == "Sales ($)":
                    formatted_val = f"${total:,.0f}"
                else:
                    formatted_val = f"{int(total):,}"
                render_kpi_card(f"{int(year)} {metric_label}", formatted_val)

    render_section_divider()

    # Bar chart comparison
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header(f"{metric_label} by {compare_by}")

    # Pivot for side-by-side comparison
    pivot_data = comparison_data.pivot(index=compare_by, columns='Year', values=metric_label).fillna(0)

    fig = go.Figure()

    colors = [COLORS['blue'], COLORS['green'], COLORS['purple'], COLORS['yellow'], COLORS['teal']]
    for idx, year in enumerate(sorted(pivot_data.columns)):
        fig.add_trace(go.Bar(
            name=str(int(year)),
            x=pivot_data.index,
            y=pivot_data[year],
            marker_color=colors[idx % len(colors)],
            text=[f"${v:,.0f}" if metric == "Sales ($)" else f"{int(v):,}" for v in pivot_data[year]],
            textposition='outside',
            textfont=dict(size=11, color='#9ca3af')
        ))

    layout = get_chart_layout(350)
    layout['barmode'] = 'group'
    layout['legend'] = dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(color='#e5e7eb', size=13))
    layout['margin'] = dict(l=10, r=10, t=40, b=80)
    layout['xaxis']['tickangle'] = -30 if len(selected_items) > 4 else 0
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # Trend over time (if comparing single item or few items)
    if len(selected_items) <= 3 and len(selected_years) >= 1:
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # Toggle between monthly and cumulative
        col1, col2 = st.columns([3, 1])
        with col1:
            render_card_header("Season Trend (Aligned by Date)")
        with col2:
            trend_type = st.selectbox("View", ["Cumulative", "Monthly"], key="comp_trend_type", label_visibility="collapsed")

        # Daily aggregation for smoother cumulative chart
        daily_data = filtered_df.groupby([group_col, 'year', filtered_df['date'].dt.date])[metric_col].sum().reset_index()
        daily_data.columns = [group_col, 'year', 'date', metric_col]
        daily_data['date'] = pd.to_datetime(daily_data['date'])
        daily_data['month'] = daily_data['date'].dt.month
        daily_data['day_of_month'] = daily_data['date'].dt.day

        # Filter to operating season (May-Nov)
        daily_data = daily_data[daily_data['month'].isin([5, 6, 7, 8, 9, 10, 11])]

        # Use a reference year (2000) to align all dates on the same x-axis
        # This makes May 1, 2025 and May 1, 2026 appear at the same x position
        REFERENCE_YEAR = 2000
        daily_data['aligned_date'] = daily_data.apply(
            lambda row: datetime(REFERENCE_YEAR, int(row['month']), int(row['day_of_month'])),
            axis=1
        )

        fig = go.Figure()

        colors = [COLORS['blue'], COLORS['green'], COLORS['purple'], COLORS['yellow'], COLORS['teal']]
        color_idx = 0

        # Create a line for each item-year combination
        for item in selected_items:
            item_data = daily_data[daily_data[group_col] == item]
            for year in sorted(item_data['year'].unique()):
                year_data = item_data[item_data['year'] == year].sort_values('aligned_date')

                if len(year_data) == 0:
                    continue

                # Calculate cumulative sum if needed
                if trend_type == "Cumulative":
                    year_data = year_data.copy()
                    year_data['value'] = year_data[metric_col].cumsum()
                else:
                    # Monthly aggregation
                    year_data = year_data.groupby('month')[metric_col].sum().reset_index()
                    year_data['value'] = year_data[metric_col]
                    year_data['month_name'] = year_data['month'].apply(lambda x: ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][x])

                label = f"{item[:20]}{'...' if len(item) > 20 else ''} ({int(year)})" if len(selected_items) > 1 else str(int(year))

                if trend_type == "Cumulative":
                    fig.add_trace(go.Scatter(
                        x=year_data['aligned_date'],
                        y=year_data['value'],
                        mode='lines',
                        name=label,
                        line=dict(width=2, color=colors[color_idx % len(colors)]),
                        hovertemplate='%{x|%b %d}: $%{y:,.0f}<extra>' + label + '</extra>' if metric == "Sales ($)" else '%{x|%b %d}: %{y:,.0f}<extra>' + label + '</extra>'
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=year_data['month_name'],
                        y=year_data['value'],
                        mode='lines+markers',
                        name=label,
                        line=dict(width=2, color=colors[color_idx % len(colors)]),
                        marker=dict(size=6)
                    ))

                color_idx += 1

        layout = get_chart_layout(350)
        layout['legend'] = dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(color='#e5e7eb', size=12))
        layout['margin'] = dict(l=10, r=10, t=40, b=30)
        layout['hovermode'] = 'x unified'

        if trend_type == "Cumulative":
            layout['xaxis']['tickformat'] = '%b %d'

        fig.update_layout(**layout)

        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Data table
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Detailed Comparison")

    # Pivot table for display - keep numeric for sorting
    pivot_display = pivot_data.copy().reset_index()

    # Rename year columns to strings for consistent column_config
    year_cols = [c for c in pivot_display.columns if c != compare_by]
    rename_map = {c: str(int(c)) for c in year_cols}
    pivot_display = pivot_display.rename(columns=rename_map)
    year_cols = [str(int(c)) for c in year_cols]

    # Add Change and Change % if we have exactly 2 years
    if len(year_cols) == 2:
        col1, col2 = sorted(year_cols)  # e.g., '2025', '2026'
        pivot_display['Change'] = pivot_display[col2] - pivot_display[col1]
        pivot_display['Change %'] = ((pivot_display[col2] - pivot_display[col1]) / pivot_display[col1].replace(0, float('nan')) * 100).fillna(0)

    # Apply conditional formatting with green/red for changes
    if metric == "Sales ($)":
        money_cols = year_cols + (['Change'] if 'Change' in pivot_display.columns else [])
        styled_df = style_dataframe_with_changes(
            pivot_display,
            money_cols=money_cols,
            pct_cols=['Change %'] if 'Change %' in pivot_display.columns else []
        )
    else:
        int_cols = year_cols + (['Change'] if 'Change' in pivot_display.columns else [])
        styled_df = style_dataframe_with_changes(
            pivot_display,
            int_cols=int_cols,
            pct_cols=['Change %'] if 'Change %' in pivot_display.columns else []
        )

    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=250)
    st.markdown('</div>', unsafe_allow_html=True)

    # ===================
    # ITEM SEASON TREND (Cumulative)
    # ===================
    render_section_divider()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Item Season Trend")

    # Item selector for trend
    col1, col2 = st.columns([2, 3])
    with col1:
        trend_items = sorted([i for i in df['plu_name'].unique() if i is not None and pd.notna(i)])
        if not trend_items:
            st.info("No items available for trend analysis.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        # Default to first selected item if available
        default_item = selected_items[0] if selected_items and selected_items[0] in trend_items else trend_items[0]
        selected_trend_item = st.selectbox("Select Item", trend_items, index=trend_items.index(default_item) if default_item in trend_items else 0, key="item_trend_select")

    # Filter data for selected item
    trend_df = df[df['plu_name'] == selected_trend_item].copy()

    # Apply attendance adjustment
    trend_df = apply_attendance_adjustment(trend_df, value_cols=['total_price', 'total_qty'])

    # Get years in the data
    trend_years = sorted(trend_df['year'].unique())

    # Create cumulative data for each year
    fig = go.Figure()

    # Reference year for alignment
    REFERENCE_YEAR = 2000

    year_colors = {
        trend_years[0] if len(trend_years) > 0 else 2025: '#3b82f6',  # Blue
        trend_years[1] if len(trend_years) > 1 else 2026: '#22c55e',  # Green
    }

    cumulative_data = {}

    # Get current year for day-of-week alignment
    current_year = datetime.now().year

    def get_day_offset_item(year):
        """Days to add to align day-of-week with current year."""
        offset = 0
        for y in range(year, current_year):
            if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
                offset += 2
            else:
                offset += 1
        return offset % 7

    for year in trend_years:
        year_data = trend_df[trend_df['year'] == year].copy()
        year_data = year_data.sort_values('date')

        # Aggregate by date
        daily = year_data.groupby(year_data['date'].dt.date)['total_price'].sum().reset_index()
        daily.columns = ['date', 'sales']
        daily['cumulative'] = daily['sales'].cumsum()

        # For past years, apply day offset to align with current year's day-of-week
        if year < current_year:
            offset = get_day_offset_item(int(year))
            daily['aligned_date'] = daily['date'].apply(
                lambda d: datetime(REFERENCE_YEAR, d.month, d.day) - timedelta(days=offset)
            )
        else:
            daily['aligned_date'] = daily['date'].apply(
                lambda d: datetime(REFERENCE_YEAR, d.month, d.day)
            )

        cumulative_data[year] = daily

        color = year_colors.get(year, '#9ca3af')

        fig.add_trace(go.Scatter(
            x=daily['aligned_date'],
            y=daily['cumulative'],
            mode='lines',
            name=str(int(year)),
            line=dict(color=color, width=2.5),
            hovertemplate=f'{int(year)}: $%{{y:,.0f}}<extra></extra>'
        ))

    # If we have exactly 2 years, find and annotate the largest discrepancies
    if len(trend_years) == 2:
        year1, year2 = trend_years[0], trend_years[1]
        df1 = cumulative_data[year1].set_index('aligned_date')
        df2 = cumulative_data[year2].set_index('aligned_date')

        # Join on aligned date
        merged = df1[['cumulative']].join(df2[['cumulative']], lsuffix='_y1', rsuffix='_y2', how='inner')

        if len(merged) > 0:
            # Calculate % difference at each point
            merged['pct_diff'] = ((merged['cumulative_y2'] - merged['cumulative_y1']) / merged['cumulative_y1'] * 100).fillna(0)

            # Only consider dates after June 10 for max/min (small sample size before then)
            june_10_cutoff = datetime(REFERENCE_YEAR, 6, 10)
            merged_after_june = merged[merged.index >= june_10_cutoff]

            # Find max positive and negative discrepancy (only after June 10)
            if len(merged_after_june) > 0:
                max_pos_idx = merged_after_june['pct_diff'].idxmax()
                max_neg_idx = merged_after_june['pct_diff'].idxmin()
                max_pos_pct = merged_after_june.loc[max_pos_idx, 'pct_diff']
                max_neg_pct = merged_after_june.loc[max_neg_idx, 'pct_diff']
            else:
                max_pos_idx = merged['pct_diff'].idxmax()
                max_neg_idx = merged['pct_diff'].idxmin()
                max_pos_pct = merged.loc[max_pos_idx, 'pct_diff']
                max_neg_pct = merged.loc[max_neg_idx, 'pct_diff']

            # Add annotations for these points
            if max_pos_pct > 0:
                fig.add_annotation(
                    x=max_pos_idx,
                    y=merged.loc[max_pos_idx, 'cumulative_y2'],
                    text=f"+{max_pos_pct:.1f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowcolor='#22c55e',
                    font=dict(color='#22c55e', size=12, weight='bold'),
                    bgcolor='rgba(34, 197, 94, 0.1)',
                    bordercolor='#22c55e',
                    borderwidth=1,
                    borderpad=4
                )

            if max_neg_pct < 0:
                fig.add_annotation(
                    x=max_neg_idx,
                    y=merged.loc[max_neg_idx, 'cumulative_y2'],
                    text=f"{max_neg_pct:.1f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowcolor='#ef4444',
                    font=dict(color='#ef4444', size=12, weight='bold'),
                    bgcolor='rgba(239, 68, 68, 0.1)',
                    bordercolor='#ef4444',
                    borderwidth=1,
                    borderpad=4
                )

    layout = get_chart_layout(350)
    layout['xaxis']['tickformat'] = '%b %d'
    layout['legend'] = dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(color='#e5e7eb', size=13))
    layout['margin'] = dict(l=10, r=10, t=40, b=30)
    layout['hovermode'] = 'x unified'
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True, key="comp_item_trend_chart")

    # Show summary for 2-year comparison
    if len(trend_years) == 2 and len(merged) > 0:
        final_y1 = merged['cumulative_y1'].iloc[-1]
        final_y2 = merged['cumulative_y2'].iloc[-1]
        final_diff = ((final_y2 - final_y1) / final_y1 * 100) if final_y1 > 0 else 0
        diff_color = "#22c55e" if final_diff >= 0 else "#ef4444"
        diff_sign = "+" if final_diff >= 0 else ""

        st.markdown(f"""
            <div style="color: #9ca3af; font-size: 14px; margin-top: 8px;">
                <span style="color: #6b7280;">Current YTD:</span>
                <span style="color: {diff_color}; font-weight: 600; margin-left: 8px;">
                    {diff_sign}{final_diff:.1f}% vs {int(year1)}
                </span>
                <span style="color: #6b7280; margin-left: 16px;">
                    (Max gain: +{max_pos_pct:.1f}% · Max gap: {max_neg_pct:.1f}%)
                </span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# TAB 3: FORECAST / ORDER PLANNING
# =============================================================================

def render_remaining_season_forecast(df):
    """Render remaining season forecast based on last year's same period."""

    st.markdown("""
        <div class="section-header">
            <div class="section-title">Remaining Season Forecast</div>
            <div class="section-subtitle">Project remaining season sales based on last year's performance for the same period</div>
        </div>
    """, unsafe_allow_html=True)

    # Get date info
    today = datetime.now()
    current_year = today.year
    last_year = current_year - 1

    # Season end is typically November 30
    season_end_month = 11
    season_end_day = 30

    # Get filter options
    categories = sorted([c for c in df['category'].unique() if c is not None and pd.notna(c)])
    subcategories = sorted([s for s in df['subcategory'].unique() if s is not None and pd.notna(s)])
    items = sorted([i for i in df['plu_name'].unique() if i is not None and pd.notna(i)])

    # Filter controls
    col1, col2, col3 = st.columns([1.2, 2.5, 1.5])

    with col1:
        filter_by = st.selectbox("Filter By", ["All Items", "Category", "Subcategory", "Specific Items"], key="rsf_filter_by")

    with col2:
        if filter_by == "Category":
            selected_filter = st.multiselect("Select Categories", categories, default=[], key="rsf_cats")
            filter_col = 'category'
        elif filter_by == "Subcategory":
            selected_filter = st.multiselect("Select Subcategories", subcategories, default=[], key="rsf_subcats")
            filter_col = 'subcategory'
        elif filter_by == "Specific Items":
            selected_filter = st.multiselect("Select Items", items, default=[], key="rsf_items", placeholder="Search items...")
            filter_col = 'plu_name'
        else:
            selected_filter = []
            filter_col = None

    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

    # Calculate last year's data from equivalent day-of-week through end of season
    # 2025 wasn't a leap year, so add 1 day to get same day of week

    # Calculate day offset (2025 = +1 day to match 2026 day of week)
    day_offset = 1  # 2025 wasn't a leap year

    # Equivalent start date in last year (same day of week as today)
    last_year_start = today.replace(year=last_year) + timedelta(days=day_offset)

    # Get last year's remaining season data
    last_year_df = df[df['year'] == last_year].copy()

    # Apply item filter if selected
    if filter_col and selected_filter:
        last_year_df = last_year_df[last_year_df[filter_col].isin(selected_filter)]

    # Filter to "equivalent today through end of season"
    last_year_remaining = last_year_df[
        (last_year_df['date'].dt.date >= last_year_start.date()) &
        (last_year_df['month'] <= season_end_month)
    ]

    # Apply attendance adjustment to prior year data (if enabled)
    last_year_remaining = apply_attendance_adjustment(last_year_remaining, value_cols=['total_price', 'total_qty'])

    if len(last_year_remaining) == 0:
        st.warning(f"No data found for {last_year} from {last_year_start.strftime('%B %d')} through end of season.")
        return

    # Also get this year's data so far for context
    this_year_df = df[df['year'] == current_year].copy()

    # Apply same filter to this year
    if filter_col and selected_filter:
        this_year_df = this_year_df[this_year_df[filter_col].isin(selected_filter)]

    # This year YTD through today
    this_year_ytd = this_year_df[this_year_df['date'].dt.date < today.date()]

    # Calculate totals
    last_year_remaining_sales = last_year_remaining['total_price'].sum()
    last_year_remaining_qty = last_year_remaining['total_qty'].sum()
    last_year_remaining_days = last_year_remaining['date'].dt.date.nunique()

    this_year_ytd_sales = this_year_ytd['total_price'].sum()
    this_year_ytd_qty = this_year_ytd['total_qty'].sum()

    # Projected full season = YTD + remaining (based on last year)
    projected_full_season = this_year_ytd_sales + last_year_remaining_sales

    # Get last year's full season for comparison (adjustment already applied via last_year_df)
    last_year_season = apply_attendance_adjustment(
        last_year_df[last_year_df['month'].isin([5, 6, 7, 8, 9, 10, 11])].copy(),
        value_cols=['total_price', 'total_qty']
    )
    last_year_full_sales = last_year_season['total_price'].sum()

    # Calculate YoY projection vs actual
    if last_year_full_sales > 0:
        projected_yoy_change = ((projected_full_season - last_year_full_sales) / last_year_full_sales) * 100
    else:
        projected_yoy_change = 0

    # KPIs
    cols = st.columns(5)
    with cols[0]:
        render_kpi_card(f"{current_year} YTD Sales", f"${this_year_ytd_sales:,.0f}")
    with cols[1]:
        render_kpi_card(f"{last_year} Remaining", f"${last_year_remaining_sales:,.0f}", f"{today.strftime('%b %d')} - Nov 30")
    with cols[2]:
        render_kpi_card(f"{current_year} Projected", f"${projected_full_season:,.0f}", f"YTD + {last_year} rest")
    with cols[3]:
        render_kpi_card(f"{last_year} Full Season", f"${last_year_full_sales:,.0f}")
    with cols[4]:
        change_sign = "+" if projected_yoy_change >= 0 else ""
        render_kpi_card("Projected YoY", f"{change_sign}{projected_yoy_change:.1f}%")

    render_section_divider()

    # Category breakdown for remaining season
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header(f"Remaining Season by Category (Based on {last_year})")

    cat_data = last_year_remaining.groupby('category').agg({
        'total_price': 'sum',
        'total_qty': 'sum'
    }).reset_index()
    cat_data.columns = ['Category', 'Projected Sales', 'Projected Qty']
    cat_data = cat_data.sort_values('Projected Sales', ascending=False)

    # Add this year YTD by category for comparison
    this_year_cat = this_year_ytd.groupby('category')['total_price'].sum().reset_index()
    this_year_cat.columns = ['Category', f'{current_year} YTD']
    cat_data = cat_data.merge(this_year_cat, on='Category', how='left')
    cat_data[f'{current_year} YTD'] = cat_data[f'{current_year} YTD'].fillna(0)
    cat_data[f'{current_year} Projected Total'] = cat_data[f'{current_year} YTD'] + cat_data['Projected Sales']

    # Rename for clarity
    cat_data = cat_data.rename(columns={'Projected Sales': f'{last_year} Remaining Sales'})

    # Export button for category data
    cat_export = cat_data[['Category', f'{current_year} YTD', f'{last_year} Remaining Sales', f'{current_year} Projected Total']].copy()
    col_space, col_excel = st.columns([5, 1])
    with col_excel:
        excel_buffer = io.BytesIO()
        cat_export.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        st.download_button("Export Excel", excel_buffer, "remaining_season_categories.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="rsf_cat_excel")

    col_config = {
        f'{last_year} Remaining Sales': st.column_config.NumberColumn(f'{last_year} Remaining', format="$%,.0f"),
        'Projected Qty': st.column_config.NumberColumn('Projected Qty', format="%,.0f"),
        f'{current_year} YTD': st.column_config.NumberColumn(f'{current_year} YTD', format="$%,.0f"),
        f'{current_year} Projected Total': st.column_config.NumberColumn(f'{current_year} Projected', format="$%,.0f"),
    }

    st.dataframe(cat_export, column_config=col_config, use_container_width=True, hide_index=True, height=300)
    st.markdown('</div>', unsafe_allow_html=True)

    # Items for remaining season (all items, not just top 25)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header(f"Items - Remaining Season Projection (Based on {last_year})")

    item_data = last_year_remaining.groupby(['plu_name', 'category', 'subcategory']).agg({
        'total_price': 'sum',
        'total_qty': 'sum'
    }).reset_index()
    item_data.columns = ['Item', 'Category', 'Subcategory', 'Projected Sales', 'Projected Qty']
    item_data = item_data.sort_values('Projected Sales', ascending=False)

    # Export button for item data
    col_space, col_excel = st.columns([5, 1])
    with col_excel:
        excel_buffer = io.BytesIO()
        item_data.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        st.download_button("Export Excel", excel_buffer, "remaining_season_items.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key="rsf_item_excel")

    col_config = {
        'Projected Sales': st.column_config.NumberColumn('Projected Sales', format="$%,.0f"),
        'Projected Qty': st.column_config.NumberColumn('Projected Qty', format="%,.0f"),
    }

    st.dataframe(item_data, column_config=col_config, use_container_width=True, hide_index=True, height=400)
    st.markdown('</div>', unsafe_allow_html=True)

    # Daily projection chart
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header(f"Remaining Season Daily Projection (Based on {last_year})")

    daily_proj = last_year_remaining.groupby(last_year_remaining['date'].dt.date)['total_price'].sum().reset_index()
    daily_proj.columns = ['date', 'sales']
    daily_proj = daily_proj.sort_values('date')

    # Create a "normalized" date for display (use current year dates)
    daily_proj['display_date'] = daily_proj['date'].apply(
        lambda d: datetime(current_year, d.month, d.day)
    )

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_proj['display_date'],
        y=daily_proj['sales'],
        mode='lines',
        name=f'{last_year} Performance',
        line=dict(color=COLORS['blue'], width=2),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.1)',
        hovertemplate='%{x|%b %d}: $%{y:,.0f}<extra></extra>'
    ))

    layout = get_chart_layout(300)
    layout['xaxis']['tickformat'] = '%b %d'
    layout['margin'] = dict(l=10, r=10, t=10, b=30)
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_forecast(df):
    """Render ordering/forecast tool - project quantities needed for upcoming days."""

    st.markdown("""
        <div class="section-header">
            <div class="section-title">Order Planning</div>
            <div class="section-subtitle">Project quantities needed based on recent sales or last year's data</div>
        </div>
    """, unsafe_allow_html=True)

    # Get date info
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    current_day = today.day

    categories = sorted([c for c in df['category'].unique() if c is not None and pd.notna(c)])
    subcategories = sorted([s for s in df['subcategory'].unique() if s is not None and pd.notna(s)])
    items = sorted([i for i in df['plu_name'].unique() if i is not None and pd.notna(i)])

    # Row 1: Selection method
    col1, col2, col3 = st.columns([1.2, 2.5, 1.5])

    with col1:
        select_by = st.selectbox("Select By", ["Item", "Subcategory", "Category", "Search"], key="order_selectby")

    with col2:
        if select_by == "Category":
            selected_items = st.multiselect("Select Categories", categories, default=[], key="order_cats")
            filter_col = 'category'
        elif select_by == "Subcategory":
            selected_items = st.multiselect("Select Subcategories", subcategories, default=[], key="order_subcats")
            filter_col = 'subcategory'
        elif select_by == "Search":
            search_term = st.text_input("Search items containing...", placeholder="e.g., burger, fries, drink", key="order_search")
            if search_term:
                matching_items = [i for i in items if search_term.lower() in i.lower()]
                selected_items = st.multiselect("Matching Items", matching_items, default=matching_items[:10], key="order_search_items")
            else:
                selected_items = []
            filter_col = 'plu_name'
        else:
            selected_items = st.multiselect("Select Items", items, default=[], key="order_items", placeholder="Search items...")
            filter_col = 'plu_name'

    with col3:
        order_days = st.number_input("Order for (days)", min_value=1, max_value=30, value=7, key="order_days")

    # Row 2: Forecast method
    col1, col2, col3, col4 = st.columns([1.5, 1.2, 1.2, 1])

    with col1:
        forecast_method = st.selectbox("Forecast Method", [
            "Recent Average (Last 7 Days)",
            "Recent Average (Last 14 Days)",
            "Recent Average (Last 30 Days)",
            "Same Period Last Year"
        ], key="order_method")

    with col2:
        buffer_pct = st.number_input("Safety Buffer %", min_value=0, max_value=50, value=10, key="order_buffer")

    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

    # Validate
    if not selected_items:
        st.info("Select items to generate order projections.")
        return

    # Filter data
    filtered_df = df[df[filter_col].isin(selected_items)]

    # Get the most recent year's data for calculations
    max_year = df['year'].max()

    # Calculate daily averages based on method
    if "Last 7 Days" in forecast_method:
        lookback_days = 7
    elif "Last 14 Days" in forecast_method:
        lookback_days = 14
    elif "Last 30 Days" in forecast_method:
        lookback_days = 30
    else:
        lookback_days = None  # Same period last year

    if lookback_days:
        # Get recent data from current year
        recent_df = filtered_df[filtered_df['year'] == max_year]
        recent_df = recent_df.sort_values('date', ascending=False)

        # Get unique recent dates
        recent_dates = recent_df['date'].dt.date.unique()[:lookback_days]

        if len(recent_dates) > 0:
            recent_df = recent_df[recent_df['date'].dt.date.isin(recent_dates)]
            daily_avg = recent_df.groupby(filter_col)['total_qty'].sum() / len(recent_dates)
        else:
            st.warning("No recent data available for selected items.")
            return
    else:
        # Same period last year
        last_year = max_year - 1
        last_year_df = filtered_df[filtered_df['year'] == last_year]

        # Filter to same time period (month/day range)
        last_year_df = last_year_df[
            (last_year_df['month'] == current_month) |
            ((last_year_df['month'] == current_month - 1) & (last_year_df['day_of_month'] >= current_day))
        ]

        if len(last_year_df) > 0:
            # Get the equivalent number of days
            unique_dates = last_year_df['date'].dt.date.nunique()
            if unique_dates > 0:
                daily_avg = last_year_df.groupby(filter_col)['total_qty'].sum() / unique_dates
            else:
                st.warning("No data from same period last year.")
                return
        else:
            st.warning("No data from same period last year.")
            return

    # Calculate projections
    projections = []
    for item in selected_items:
        if item in daily_avg.index:
            avg_qty = daily_avg[item]
            projected_qty = avg_qty * order_days
            with_buffer = projected_qty * (1 + buffer_pct / 100)

            projections.append({
                'Item': item,
                'Daily Avg': round(avg_qty, 1),
                f'Projected ({order_days} days)': round(projected_qty, 0),
                f'With {buffer_pct}% Buffer': round(with_buffer, 0)
            })

    if not projections:
        st.warning("No data available for selected items.")
        return

    proj_df = pd.DataFrame(projections)

    # Summary KPIs
    total_projected = proj_df[f'Projected ({order_days} days)'].sum()
    total_with_buffer = proj_df[f'With {buffer_pct}% Buffer'].sum()
    avg_daily_total = proj_df['Daily Avg'].sum()

    cols = st.columns(4)
    with cols[0]:
        render_kpi_card("Items Selected", f"{len(projections)}")
    with cols[1]:
        render_kpi_card("Avg Daily Total", f"{avg_daily_total:,.0f}")
    with cols[2]:
        render_kpi_card("Projected Total", f"{total_projected:,.0f}")
    with cols[3]:
        render_kpi_card("Order Qty (+Buffer)", f"{total_with_buffer:,.0f}")

    render_section_divider()

    # Projection table
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Order Projections")

    # Format for display
    display_df = proj_df.copy()
    display_df['Daily Avg'] = display_df['Daily Avg'].apply(lambda x: f"{x:,.1f}")
    display_df[f'Projected ({order_days} days)'] = display_df[f'Projected ({order_days} days)'].apply(lambda x: f"{int(x):,}")
    display_df[f'With {buffer_pct}% Buffer'] = display_df[f'With {buffer_pct}% Buffer'].apply(lambda x: f"{int(x):,}")

    st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

    # Export button
    col_space, col_excel = st.columns([5, 1])
    with col_excel:
        excel_buffer = io.BytesIO()
        proj_df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        st.download_button("Export Excel", excel_buffer, "order_projections.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Bar chart of top items
    if len(proj_df) > 1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        render_card_header(f"Top Items by Projected Quantity")

        chart_df = proj_df.nlargest(15, f'Projected ({order_days} days)')

        fig = go.Figure(go.Bar(
            x=chart_df[f'Projected ({order_days} days)'],
            y=chart_df['Item'],
            orientation='h',
            marker_color=COLORS['green'],
            text=[f"{int(v):,}" for v in chart_df[f'Projected ({order_days} days)']],
            textposition='outside',
            textfont=dict(size=11, color='#9ca3af')
        ))

        layout = get_chart_layout(min(400, len(chart_df) * 35 + 50))
        layout['yaxis']['showgrid'] = False
        layout['margin'] = dict(l=10, r=60, t=10, b=10)
        fig.update_layout(**layout)

        st.plotly_chart(fig, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# TAB 4: ITEMS
# =============================================================================

def render_items(df):
    """Render items tab with sortable table matching inventory dashboard style."""

    st.markdown("""
        <div class="section-header">
            <div class="section-title">All Items</div>
            <div class="section-subtitle">Browse and filter item sales data</div>
        </div>
    """, unsafe_allow_html=True)

    # Get current date info for YTD calculations
    today = datetime.now()
    current_month = today.month
    current_day = today.day

    # Get filter options (filter out None/NaN values)
    years = sorted([y for y in df['year'].unique() if y is not None and pd.notna(y)])
    categories = sorted([c for c in df['category'].unique() if c is not None and pd.notna(c)])

    # Filters row - 5 columns now
    col1, col2, col3, col4, col5 = st.columns([1.2, 1.2, 1.2, 1.2, 1])

    with col1:
        date_range = st.selectbox("Date Range", ['Year to Date', 'Full Year', 'Custom Range'], key="items_daterange")

    with col2:
        if date_range == 'Year to Date':
            # For YTD, allow selecting years to compare - default to all years
            ytd_years = st.multiselect("Years", [str(y) for y in years], default=[str(y) for y in years], key="items_ytd_years")
            selected_year = 'All Years'  # Not used in YTD mode
        else:
            selected_year = st.selectbox("Year", ['All Years'] + [str(y) for y in years], key="items_year")
            ytd_years = []  # Not used in non-YTD mode

    with col3:
        selected_cat = st.selectbox("Category", ['All Categories'] + list(categories), key="items_cat")

    with col4:
        # Get subcategories based on selected category (filter out None/NaN)
        if selected_cat != 'All Categories':
            subcats = sorted([s for s in df[df['category'] == selected_cat]['subcategory'].unique() if s is not None and pd.notna(s)])
        else:
            subcats = sorted([s for s in df['subcategory'].unique() if s is not None and pd.notna(s)])
        selected_subcat = st.selectbox("Subcategory", ['All Subcategories'] + list(subcats), key="items_subcat")

    with col5:
        # Download button at the end
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)

    # Apply filters
    filtered = df.copy()

    # Date range filtering
    if date_range == 'Year to Date':
        # Filter to selected years, using week-based comparison (Saturday to Saturday)
        if ytd_years:
            year_list = [int(y) for y in ytd_years]
            filtered = filtered[filtered['year'].isin(year_list)]
            # Filter to YTD by week number and day of week for apples-to-apples comparison
            filtered = filter_ytd_same_dow(filtered)
    elif date_range == 'Custom Range':
        # Show date inputs for custom range
        col_start, col_end = st.columns(2)
        with col_start:
            start_date = st.date_input("Start Date", value=df['date'].min().date(), key="items_start")
        with col_end:
            end_date = st.date_input("End Date", value=df['date'].max().date(), key="items_end")
        filtered = filtered[(filtered['date'].dt.date >= start_date) & (filtered['date'].dt.date <= end_date)]
    else:
        # Full Year
        if selected_year != 'All Years':
            filtered = filtered[filtered['year'] == int(selected_year)]

    # Category/Subcategory filters
    if selected_cat != 'All Categories':
        filtered = filtered[filtered['category'] == selected_cat]
    if selected_subcat != 'All Subcategories':
        filtered = filtered[filtered['subcategory'] == selected_subcat]

    # Apply attendance adjustment to prior years (if enabled)
    filtered = apply_attendance_adjustment(filtered, value_cols=['total_price', 'total_qty'])

    # Only include items with sales > 0
    filtered = filtered[filtered['total_price'] > 0]

    # Aggregate by item (and year for YTD comparison)
    if date_range == 'Year to Date' and len(ytd_years) > 1:
        # Group by item AND year for comparison
        item_data = filtered.groupby(['plu', 'plu_name', 'category', 'subcategory', 'year']).agg({
            'total_qty': 'sum',
            'total_price': 'sum'
        }).reset_index()
        item_data.columns = ['PLU', 'Item', 'Category', 'Subcategory', 'Year', 'Qty Sold', 'Sales']

        # Pivot to show years side by side
        pivot_qty = item_data.pivot_table(index=['PLU', 'Item', 'Category', 'Subcategory'],
                                          columns='Year', values='Qty Sold', fill_value=0)
        pivot_sales = item_data.pivot_table(index=['PLU', 'Item', 'Category', 'Subcategory'],
                                            columns='Year', values='Sales', fill_value=0)

        # Rename columns
        pivot_qty.columns = [f'Qty {int(y)}' for y in pivot_qty.columns]
        pivot_sales.columns = [f'Sales {int(y)}' for y in pivot_sales.columns]

        # Combine
        item_data = pivot_qty.join(pivot_sales).reset_index()

        # Calculate total sales for sorting
        sales_cols = [c for c in item_data.columns if c.startswith('Sales')]
        item_data['_total_sales'] = item_data[sales_cols].sum(axis=1)
        item_data = item_data.sort_values('_total_sales', ascending=False)

        # Calculate Change and Change % if we have exactly 2 years
        if len(sales_cols) == 2:
            col1, col2 = sorted(sales_cols)  # e.g., 'Sales 2025', 'Sales 2026'
            item_data['Change'] = item_data[col2] - item_data[col1]
            item_data['Change %'] = ((item_data[col2] - item_data[col1]) / item_data[col1].replace(0, float('nan')) * 100).fillna(0)

        # Calculate totals
        total_items = len(item_data)
        total_sales = item_data['_total_sales'].sum()
        qty_cols = [c for c in item_data.columns if c.startswith('Qty')]
        total_qty = item_data[qty_cols].sum().sum()

        item_data = item_data.drop(columns=['_total_sales'])
    else:
        # Standard aggregation
        item_data = filtered.groupby(['plu', 'plu_name', 'category', 'subcategory']).agg({
            'total_qty': 'sum',
            'total_price': 'sum'
        }).reset_index()
        item_data.columns = ['PLU', 'Item', 'Category', 'Subcategory', 'Qty Sold', 'Sales']

        # Calculate avg price and sort by sales descending
        item_data['Avg Price'] = item_data['Sales'] / item_data['Qty Sold']
        item_data['Avg Price'] = item_data['Avg Price'].fillna(0)
        item_data = item_data.sort_values('Sales', ascending=False)

        # Summary stats
        total_items = len(item_data)
        total_qty = item_data['Qty Sold'].sum()
        total_sales = item_data['Sales'].sum()

    avg_price = total_sales / total_qty if total_qty > 0 else 0

    # Summary KPIs - show year comparison if both years selected
    if date_range == 'Year to Date' and len(ytd_years) == 2:
        year1, year2 = sorted([int(y) for y in ytd_years])
        sales_y1 = filtered[filtered['year'] == year1]['total_price'].sum()
        sales_y2 = filtered[filtered['year'] == year2]['total_price'].sum()
        change_dollars = sales_y2 - sales_y1
        change_pct = ((sales_y2 - sales_y1) / sales_y1 * 100) if sales_y1 > 0 else 0
        change_sign = "+" if change_dollars >= 0 else ""

        cols = st.columns(4)
        with cols[0]:
            render_kpi_card(f"{year1} Sales", f"${sales_y1:,.0f}")
        with cols[1]:
            render_kpi_card(f"{year2} Sales", f"${sales_y2:,.0f}")
        with cols[2]:
            render_kpi_card("$ Change", f"{change_sign}${change_dollars:,.0f}")
        with cols[3]:
            render_kpi_card("% Change", f"{change_sign}{change_pct:.1f}%")
    else:
        cols = st.columns(4)
        with cols[0]:
            render_kpi_card("Total Items", f"{total_items:,}")
        with cols[1]:
            render_kpi_card("Total Sold", f"{total_qty:,.0f}")
        with cols[2]:
            render_kpi_card("Total Sales", f"${total_sales:,.0f}")
        with cols[3]:
            render_kpi_card("Avg Price", f"${avg_price:.2f}")

    render_section_divider()

    # Export button row
    col_space, col_excel = st.columns([5, 1])
    with col_excel:
        excel_buffer = io.BytesIO()
        item_data.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        st.download_button("Export Excel", excel_buffer, "items_export.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # Prepare display data - keep numeric for proper sorting
    if date_range == 'Year to Date' and len(ytd_years) > 1:
        # For YTD comparison, show the pivot table with Change columns if 2 years
        base_cols = ['Item', 'Category', 'Subcategory'] + [c for c in item_data.columns if c.startswith('Qty') or c.startswith('Sales')]
        # Add Change columns if they exist
        if 'Change' in item_data.columns:
            display_cols = base_cols + ['Change', 'Change %']
        else:
            display_cols = base_cols
        display_data = item_data[display_cols].copy()

        # Apply conditional formatting with green/red for changes
        sales_cols = [c for c in display_data.columns if c.startswith('Sales')]
        qty_cols = [c for c in display_data.columns if c.startswith('Qty')]
        money_cols = sales_cols + (['Change'] if 'Change' in display_data.columns else [])

        styled_df = style_dataframe_with_changes(
            display_data,
            money_cols=money_cols,
            int_cols=qty_cols,
            pct_cols=['Change %'] if 'Change %' in display_data.columns else []
        )

        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=500)
    else:
        # Standard display
        display_data = item_data[['Item', 'Category', 'Subcategory', 'Qty Sold', 'Sales', 'Avg Price']].copy()

        # Column config for proper formatting AND sorting (with commas)
        col_config = {
            'Qty Sold': st.column_config.NumberColumn('Qty Sold', format="%,.0f"),
            'Sales': st.column_config.NumberColumn('Sales', format="$%,.0f"),
            'Avg Price': st.column_config.NumberColumn('Avg Price', format="$%.2f"),
        }

        st.dataframe(
            display_data,
            column_config=col_config,
            use_container_width=True,
            hide_index=True,
            height=500
        )

    # ===================
    # ITEM SEASON TREND (Cumulative)
    # ===================
    render_section_divider()

    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Item Season Trend")

    # Item selector for trend
    col1, col2 = st.columns([2, 3])
    with col1:
        trend_items = sorted([i for i in df['plu_name'].unique() if i is not None and pd.notna(i)])
        if not trend_items:
            st.info("No items available for trend analysis.")
            st.markdown('</div>', unsafe_allow_html=True)
            return
        selected_trend_item = st.selectbox("Select Item", trend_items, key="items_trend_select")

    # Filter data for selected item
    trend_df = df[df['plu_name'] == selected_trend_item].copy()

    # Apply attendance adjustment
    trend_df = apply_attendance_adjustment(trend_df, value_cols=['total_price', 'total_qty'])

    # Get years in the data
    trend_years = sorted(trend_df['year'].unique())

    if len(trend_years) == 0:
        st.info("No data available for this item.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Create cumulative data for each year
    fig = go.Figure()

    # Reference year for alignment
    REFERENCE_YEAR = 2000

    year_colors = {
        trend_years[0] if len(trend_years) > 0 else 2025: '#3b82f6',  # Blue
        trend_years[1] if len(trend_years) > 1 else 2026: '#22c55e',  # Green
    }

    cumulative_data = {}

    # Get current year for day-of-week alignment
    current_year = datetime.now().year

    def get_day_offset_items(year):
        """Days to add to align day-of-week with current year."""
        offset = 0
        for y in range(year, current_year):
            if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
                offset += 2
            else:
                offset += 1
        return offset % 7

    for year in trend_years:
        year_data = trend_df[trend_df['year'] == year].copy()
        year_data = year_data.sort_values('date')

        # Aggregate by date
        daily = year_data.groupby(year_data['date'].dt.date)['total_price'].sum().reset_index()
        daily.columns = ['date', 'sales']
        daily['cumulative'] = daily['sales'].cumsum()

        # For past years, apply day offset to align with current year's day-of-week
        if year < current_year:
            offset = get_day_offset_items(int(year))
            daily['aligned_date'] = daily['date'].apply(
                lambda d: datetime(REFERENCE_YEAR, d.month, d.day) - timedelta(days=offset)
            )
        else:
            daily['aligned_date'] = daily['date'].apply(
                lambda d: datetime(REFERENCE_YEAR, d.month, d.day)
            )

        cumulative_data[year] = daily

        color = year_colors.get(year, '#9ca3af')

        fig.add_trace(go.Scatter(
            x=daily['aligned_date'],
            y=daily['cumulative'],
            mode='lines',
            name=str(int(year)),
            line=dict(color=color, width=2.5),
            hovertemplate=f'{int(year)}: $%{{y:,.0f}}<extra></extra>'
        ))

    # Variables for summary (initialize)
    max_pos_pct = 0
    max_neg_pct = 0
    merged = pd.DataFrame()

    # If we have exactly 2 years, find and annotate the largest discrepancies
    if len(trend_years) == 2:
        year1, year2 = trend_years[0], trend_years[1]
        df1 = cumulative_data[year1].set_index('aligned_date')
        df2 = cumulative_data[year2].set_index('aligned_date')

        # Join on aligned date
        merged = df1[['cumulative']].join(df2[['cumulative']], lsuffix='_y1', rsuffix='_y2', how='inner')

        if len(merged) > 0:
            # Calculate % difference at each point
            merged['pct_diff'] = ((merged['cumulative_y2'] - merged['cumulative_y1']) / merged['cumulative_y1'] * 100).fillna(0)

            # Only consider dates after June 10 for max/min (small sample size before then)
            june_10_cutoff = datetime(REFERENCE_YEAR, 6, 10)
            merged_after_june = merged[merged.index >= june_10_cutoff]

            # Find max positive and negative discrepancy (only after June 10)
            if len(merged_after_june) > 0:
                max_pos_idx = merged_after_june['pct_diff'].idxmax()
                max_neg_idx = merged_after_june['pct_diff'].idxmin()
                max_pos_pct = merged_after_june.loc[max_pos_idx, 'pct_diff']
                max_neg_pct = merged_after_june.loc[max_neg_idx, 'pct_diff']
            else:
                max_pos_idx = merged['pct_diff'].idxmax()
                max_neg_idx = merged['pct_diff'].idxmin()
                max_pos_pct = merged.loc[max_pos_idx, 'pct_diff']
                max_neg_pct = merged.loc[max_neg_idx, 'pct_diff']

            # Add annotations for these points
            if max_pos_pct > 0:
                fig.add_annotation(
                    x=max_pos_idx,
                    y=merged.loc[max_pos_idx, 'cumulative_y2'],
                    text=f"+{max_pos_pct:.1f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowcolor='#22c55e',
                    font=dict(color='#22c55e', size=12, weight='bold'),
                    bgcolor='rgba(34, 197, 94, 0.1)',
                    bordercolor='#22c55e',
                    borderwidth=1,
                    borderpad=4
                )

            if max_neg_pct < 0:
                fig.add_annotation(
                    x=max_neg_idx,
                    y=merged.loc[max_neg_idx, 'cumulative_y2'],
                    text=f"{max_neg_pct:.1f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowcolor='#ef4444',
                    font=dict(color='#ef4444', size=12, weight='bold'),
                    bgcolor='rgba(239, 68, 68, 0.1)',
                    bordercolor='#ef4444',
                    borderwidth=1,
                    borderpad=4
                )

    layout = get_chart_layout(350)
    layout['xaxis']['tickformat'] = '%b %d'
    layout['legend'] = dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(color='#e5e7eb', size=13))
    layout['margin'] = dict(l=10, r=10, t=40, b=30)
    layout['hovermode'] = 'x unified'
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True, key="items_tab_trend_chart")

    # Show summary for 2-year comparison
    if len(trend_years) == 2 and len(merged) > 0:
        final_y1 = merged['cumulative_y1'].iloc[-1]
        final_y2 = merged['cumulative_y2'].iloc[-1]
        final_diff = ((final_y2 - final_y1) / final_y1 * 100) if final_y1 > 0 else 0
        diff_color = "#22c55e" if final_diff >= 0 else "#ef4444"
        diff_sign = "+" if final_diff >= 0 else ""

        st.markdown(f"""
            <div style="color: #9ca3af; font-size: 14px; margin-top: 8px;">
                <span style="color: #6b7280;">Current YTD:</span>
                <span style="color: {diff_color}; font-weight: 600; margin-left: 8px;">
                    {diff_sign}{final_diff:.1f}% vs {int(year1)}
                </span>
                <span style="color: #6b7280; margin-left: 16px;">
                    (Max gain: +{max_pos_pct:.1f}% · Max gap: {max_neg_pct:.1f}%)
                </span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# TAB 5: UPLOAD DATA
# =============================================================================

def process_uploaded_file(file_bytes, filename):
    """
    Process a single uploaded Excel file and return (date, dataframe) or (None, None).
    Uses same parsing logic as ingest.py.
    """
    import re
    import pytz
    ET = pytz.timezone('America/New_York')

    try:
        # Read raw to get the date from row 2
        df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None, nrows=10)

        # Extract date from row 2
        cell_value = str(df_raw.iloc[1, 0])
        pattern = r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})'
        match = re.search(pattern, cell_value)

        if not match:
            return None, None, "Could not parse date from file"

        month_str, day_str, year_str = match.groups()
        date_str = f"{month_str} {day_str}, {year_str}"
        dt = datetime.strptime(date_str, "%B %d, %Y")
        operating_date = ET.localize(dt.replace(hour=12))

        # Read the actual data starting from row 7
        df = pd.read_excel(io.BytesIO(file_bytes), header=6)
        df.columns = [str(c).strip() for c in df.columns]

        # Map columns
        col_mapping = {}
        for col in df.columns:
            col_lower = col.lower()
            if col_lower == 'plu':
                col_mapping[col] = 'plu'
            elif 'pluname' in col_lower or 'plu name' in col_lower:
                col_mapping[col] = 'plu_name'
            elif 'sold' in col_lower and 'qty' in col_lower:
                col_mapping[col] = 'sold_qty'
            elif 'returned' in col_lower and 'qty' in col_lower:
                col_mapping[col] = 'returned_qty'
            elif col_lower == 'total qty' or col_lower == 'totalqty':
                col_mapping[col] = 'total_qty'
            elif 'average' in col_lower and 'price' in col_lower:
                col_mapping[col] = 'average_price'
            elif col_lower == 'total price' or col_lower == 'totalprice':
                col_mapping[col] = 'total_price'

        df = df.rename(columns=col_mapping)

        expected_cols = ['plu', 'plu_name', 'sold_qty', 'returned_qty', 'total_qty', 'average_price', 'total_price']
        available_cols = [c for c in expected_cols if c in df.columns]
        df = df[available_cols]

        # Remove total row
        if len(df) > 0:
            df = df[~df['plu'].astype(str).str.lower().str.contains('total', na=False)]

        # Convert numeric columns
        for col in ['sold_qty', 'returned_qty', 'total_qty', 'average_price', 'total_price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df['date'] = operating_date

        return operating_date, df, None

    except Exception as e:
        return None, None, str(e)


def add_features_to_df(df):
    """Add feature columns to a dataframe (inline version of features.py)."""
    import pytz
    ET = pytz.timezone('America/New_York')

    df = df.copy()

    # Basic date features
    df['day_of_week'] = df['date'].dt.day_name()
    df['day_of_week_num'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['month_name'] = df['date'].dt.month_name()
    df['year'] = df['date'].dt.year
    df['day_of_month'] = df['date'].dt.day
    df['is_weekend'] = df['day_of_week_num'].isin([5, 6]).astype(int)

    # Week of season
    def calc_week_of_season(row):
        season_start = ET.localize(datetime(int(row['year']), 5, 1, 12, 0, 0))
        delta = row['date'] - season_start
        return max(1, (delta.days // 7) + 1)

    df['week_of_season'] = df.apply(calc_week_of_season, axis=1)

    # Per-capita metrics (attendance may be NULL)
    df['attendance'] = df.get('attendance', pd.Series([None] * len(df)))
    df['revenue_per_capita'] = df['total_price'] / df['attendance'].replace(0, float('nan'))
    df['qty_per_capita'] = df['total_qty'] / df['attendance'].replace(0, float('nan'))
    df['revenue_per_capita'] = df['revenue_per_capita'].fillna(0)
    df['qty_per_capita'] = df['qty_per_capita'].fillna(0)

    # Rolling features (simplified - will be recalculated on full data)
    df['rolling_7day_avg_qty'] = df['total_qty']
    df['rolling_7day_avg_attendance'] = df['attendance'].fillna(0)

    return df


def merge_into_database(new_df):
    """
    Merge new data into the database, handling duplicates by date/plu.
    Works with both SQLite (local) and PostgreSQL (Supabase cloud).
    """
    # Convert date to string for storage
    new_df = new_df.copy()
    new_df['date'] = new_df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Drop artifact rows with no PLU (blank/total rows parse as NaN)
    new_df = new_df[new_df['plu'].notna()]

    # psycopg v3 strictly types parameters: a float NaN in a text column raises
    # DatatypeMismatch. Convert NaN -> None in text columns so they bind as NULL.
    for col in new_df.select_dtypes(include=['object']).columns:
        new_df[col] = new_df[col].where(pd.notna(new_df[col]), None)

    # Keep numeric feature columns as float to match the existing table schema
    # (all-NULL attendance can otherwise make these come through as integers).
    for col in ['attendance', 'revenue_per_capita', 'qty_per_capita',
                'rolling_7day_avg_qty', 'rolling_7day_avg_attendance']:
        if col in new_df.columns:
            new_df[col] = pd.to_numeric(new_df[col], errors='coerce').astype('float64')

    if new_df.empty:
        return

    # Check if table exists
    if not table_exists('sales_featured'):
        # Create table with first upload
        save_dataframe(new_df, 'sales_featured', if_exists='replace')
    else:
        # Delete existing records for the same dates (to handle duplicates)
        dates = list(new_df['date'].unique())
        delete_by_dates('sales_featured', dates)

        # Insert new records
        save_dataframe(new_df, 'sales_featured', if_exists='append')


def render_upload_compact():
    """Compact upload interface for popover."""

    st.markdown("**Item Sales**")
    st.caption("Daily sales Excel files")
    item_files = st.file_uploader("Items", type=['xlsx'], accept_multiple_files=True, key="popup_items", label_visibility="collapsed")

    if item_files:
        if st.button(f"Process {len(item_files)} item file(s)", type="primary", use_container_width=True, key="popup_items_btn"):
            progress = st.progress(0, text="Processing...")
            processed = 0
            all_data = []
            dates_processed = []

            for i, f in enumerate(item_files):
                progress.progress((i + 1) / len(item_files))
                file_bytes = f.read()
                operating_date, df, error = process_uploaded_file(file_bytes, f.name)
                if operating_date is not None and df is not None and len(df) > 0:
                    df = add_features_to_df(df)
                    all_data.append(df)
                    dates_processed.append(operating_date.strftime('%Y-%m-%d'))
                    processed += 1

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                merge_into_database(combined_df)
                progress.empty()
                st.success(f"Processed {processed} file(s)")
                st.caption(f"Dates: {', '.join(sorted(dates_processed))}")
                st.info("Refresh page to see updated data")

    st.markdown("---")
    st.markdown("**Location Sales**")
    st.caption("Daily F&B Sales by Location files")
    loc_files = st.file_uploader("Locations", type=['xlsx'], accept_multiple_files=True, key="popup_locs", label_visibility="collapsed")

    if loc_files:
        if st.button(f"Process {len(loc_files)} location file(s)", type="primary", use_container_width=True, key="popup_locs_btn"):
            process_location_uploads(loc_files)


def render_upload():
    """Render file upload tab with auto-processing."""

    st.markdown("""
        <div class="section-header">
            <div class="section-title">Data Management</div>
            <div class="section-subtitle">Upload sales files - data is processed automatically</div>
        </div>
    """, unsafe_allow_html=True)

    # Show database mode
    db_mode = get_db_info()
    st.markdown(f"<p style='color: #6b7280; font-size: 13px; margin-bottom: 12px;'>📡 Database: {db_mode}</p>", unsafe_allow_html=True)

    # Current data status (2025, 2026 only for now)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Current Data (2025-2026)")

    if db_exists():
        try:
            year_data = read_sql("""
                SELECT year, COUNT(DISTINCT date) as days, SUM(total_price) as revenue
                FROM sales_featured
                WHERE year >= 2025
                GROUP BY year ORDER BY year
            """)
            if len(year_data) > 0:
                # Rename columns for display
                year_data.columns = ['Year', 'Days', 'Revenue']
                year_data['Revenue'] = year_data['Revenue'].apply(lambda x: f"${x:,.0f}")
                st.dataframe(year_data, use_container_width=True, hide_index=True, height=120)
            else:
                st.info("No 2025-2026 data yet. Upload files to get started.")
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.info("No database found. Upload files to get started.")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)

    # Upload section
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Upload Sales Files")

    st.markdown("""
        <p style='color: #9ca3af; font-size: 15px; margin-bottom: 16px;'>
            Upload daily sales Excel files. Files are processed immediately and added to the database.<br>
            <span style='color: #6b7280; font-size: 13px;'>• Duplicate dates are automatically updated (most recent upload wins)<br>
            • Upload multiple files at once - they'll all be processed<br>
            • Data reflects across all tabs immediately after processing</span>
        </p>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader("Drop Excel files here", type=['xlsx'], accept_multiple_files=True, label_visibility="collapsed")

    if uploaded_files:
        if st.button(f"Process {len(uploaded_files)} file(s)", type="primary", use_container_width=True):
            progress = st.progress(0, text="Processing files...")

            processed = 0
            skipped = 0
            errors = []
            all_data = []
            dates_processed = []

            for i, f in enumerate(uploaded_files):
                progress.progress((i + 1) / len(uploaded_files), text=f"Processing {f.name}...")

                file_bytes = f.read()
                operating_date, df, error = process_uploaded_file(file_bytes, f.name)

                if error:
                    errors.append(f"{f.name}: {error}")
                    skipped += 1
                elif operating_date is not None and df is not None and len(df) > 0:
                    # Add features
                    df = add_features_to_df(df)
                    all_data.append(df)
                    dates_processed.append(operating_date.strftime('%Y-%m-%d'))
                    processed += 1

                    # Also save the raw file to the sales folder for backup (local mode only)
                    if not is_cloud_mode():
                        try:
                            path = SALES_FOLDER / f.name
                            with open(path, 'wb') as out:
                                out.write(file_bytes)
                        except:
                            pass
                else:
                    skipped += 1

            # Merge all data into database
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                merge_into_database(combined_df)

                progress.empty()

                # Success message
                st.success(f"✅ Processed {processed} file(s) successfully!")
                if dates_processed:
                    st.markdown(f"<p style='color: #9ca3af; font-size: 14px;'>Dates added/updated: {', '.join(sorted(dates_processed))}</p>", unsafe_allow_html=True)

                if skipped > 0:
                    st.warning(f"⚠️ Skipped {skipped} file(s)")

                if errors:
                    with st.expander("View errors"):
                        for err in errors:
                            st.text(err)

                st.info("🔄 Refresh the page to see updated data in all tabs.")
            else:
                progress.empty()
                st.error("No files could be processed. Check file format.")

    st.markdown('</div>', unsafe_allow_html=True)

    # Location Sales Upload Section
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Upload Location Sales Files")

    st.markdown("""
        <p style='color: #9ca3af; font-size: 15px; margin-bottom: 16px;'>
            Upload location sales Excel files (from the Daily F&B Sales by Location email).<br>
            <span style='color: #6b7280; font-size: 13px;'>• Date is automatically extracted from within the file</span>
        </p>
    """, unsafe_allow_html=True)

    location_files = st.file_uploader("Drop location files here", type=['xlsx'], accept_multiple_files=True, key="loc_upload_main", label_visibility="collapsed")

    if location_files:
        if st.button(f"Process {len(location_files)} location file(s)", type="primary", use_container_width=True):
            process_location_uploads(location_files)

    st.markdown('</div>', unsafe_allow_html=True)

    # Info about data sharing status
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Data Sync Status")

    if is_cloud_mode():
        st.markdown("""
            <p style='color: #22c55e; font-size: 14px;'>
                ✅ <strong>Cloud Mode Active</strong> - Data syncs across all devices instantly.<br>
                <span style='color: #9ca3af;'>Uploads from any device are immediately visible to everyone.</span>
            </p>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <p style='color: #9ca3af; font-size: 14px;'>
                📁 <strong style='color: #e5e7eb;'>Local Mode</strong> - Data is stored on this device only.<br>
                <span style='color: #6b7280;'>Deploy to Streamlit Cloud + Supabase for multi-device sync.</span>
            </p>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# =============================================================================
# TAB 6: LOCATIONS
# =============================================================================

def load_location_data():
    """Load location sales data from database."""
    if not db_exists():
        return None
    try:
        df = read_sql("SELECT * FROM location_sales")
        if len(df) == 0:
            return None
        df['date'] = pd.to_datetime(df['date'])
        return df
    except:
        return None


def process_location_file(file_bytes, filename):
    """
    Process a location sales Excel file.
    Extracts location (Agency Name) and gross_sales (Sales Gross) columns.
    File format: Date in row 2, Header row at row 7 (0-indexed), data starts at row 8.
    Returns (date, dataframe) or (None, None, error).
    """
    import pytz
    ET = pytz.timezone('America/New_York')

    try:
        # First, try to get date from the file itself (row 2 has date info)
        df_raw = pd.read_excel(io.BytesIO(file_bytes), header=None, nrows=5)

        operating_date = None

        # Try to parse date from row 2 (FromDate Friday, August 15, 2025)
        try:
            date_cell = str(df_raw.iloc[2, 0])
            date_pattern = r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})'
            match = re.search(date_pattern, date_cell)
            if match:
                month_str, day_str, year_str = match.groups()
                date_str = f"{month_str} {day_str}, {year_str}"
                dt = datetime.strptime(date_str, "%B %d, %Y")
                operating_date = ET.localize(dt.replace(hour=12))
        except:
            pass

        # Fallback to filename date
        if operating_date is None:
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
            if date_match:
                date_str = date_match.group(1)
                operating_date = ET.localize(datetime.strptime(date_str, "%Y-%m-%d").replace(hour=12))
            else:
                return None, None, "Could not parse date from file or filename"

        # Read the actual data - header is at row 7
        df = pd.read_excel(io.BytesIO(file_bytes), header=7)
        df.columns = [str(c).strip() for c in df.columns]

        # Find the Agency Name and Sales Gross columns
        location_col = None
        sales_col = None

        for col in df.columns:
            col_lower = col.lower().strip()
            if 'agency name' in col_lower or col_lower == 'agency name':
                location_col = col
            if 'sales gross' in col_lower or col_lower == 'sales gross':
                sales_col = col

        if not location_col or not sales_col:
            return None, None, f"Could not find required columns. Found: {list(df.columns)}"

        # Keep only the columns we need
        result_df = df[[location_col, sales_col]].copy()
        result_df.columns = ['location', 'gross_sales']

        # Convert sales to positive numbers (they come as negatives)
        result_df['gross_sales'] = pd.to_numeric(result_df['gross_sales'], errors='coerce').fillna(0).abs()

        # Remove empty rows and total rows
        result_df = result_df[result_df['location'].notna() & (result_df['location'] != '')]
        result_df = result_df[~result_df['location'].astype(str).str.lower().str.contains('total', na=False)]

        # Add date and features
        result_df['date'] = operating_date
        result_df['year'] = operating_date.year
        result_df['month'] = operating_date.month
        result_df['day_of_week'] = operating_date.strftime('%A')
        result_df['day_of_week_num'] = operating_date.weekday()

        return operating_date, result_df, None

    except Exception as e:
        return None, None, str(e)


def merge_location_data(new_df):
    """Merge location data into database, handling duplicates by date/location."""
    new_df = new_df.copy()
    new_df['date'] = new_df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Delete existing records for the same dates
    dates = list(new_df['date'].unique())
    delete_by_dates('location_sales', dates)

    # Insert new records
    save_dataframe(new_df, 'location_sales', if_exists='append')


def render_locations():
    """Render the Locations tab with sales by location data."""

    st.markdown("""
        <div class="section-header">
            <div class="section-title">Location Sales</div>
            <div class="section-subtitle">Sales performance by location</div>
        </div>
    """, unsafe_allow_html=True)

    # Load location data
    loc_df = load_location_data()

    if loc_df is None or len(loc_df) == 0:
        st.info("No location data yet. Upload location sales files below.")

        # Show upload section
        st.markdown('<div class="card">', unsafe_allow_html=True)
        render_card_header("Upload Location Sales Files")

        st.markdown("""
            <p style='color: #9ca3af; font-size: 15px; margin-bottom: 16px;'>
                Upload location sales Excel files (from the Daily F&B Sales by Location email).<br>
                <span style='color: #6b7280; font-size: 13px;'>Files should be named like: Location_Sales_2026-08-21.xlsx</span>
            </p>
        """, unsafe_allow_html=True)

        uploaded_files = st.file_uploader("Drop location files here", type=['xlsx'], accept_multiple_files=True, key="loc_upload", label_visibility="collapsed")

        if uploaded_files:
            if st.button(f"Process {len(uploaded_files)} location file(s)", type="primary", use_container_width=True):
                process_location_uploads(uploaded_files)

        st.markdown('</div>', unsafe_allow_html=True)
        return

    # Filter to days with >$10k gross sales
    daily_totals = loc_df.groupby(loc_df['date'].dt.date)['gross_sales'].sum()
    valid_dates = daily_totals[daily_totals > 10000].index
    loc_df = loc_df[loc_df['date'].dt.date.isin(valid_dates)]

    # Get current date info for YTD
    today = datetime.now()
    current_month = today.month
    current_day = today.day

    # Filter options
    years = sorted([y for y in loc_df['year'].unique() if y is not None and pd.notna(y)])

    col1, col2, col3, col4 = st.columns([1.2, 1.5, 1, 1])

    with col1:
        date_range = st.selectbox("Date Range", ['Year to Date', 'Full Season (May-Nov)', 'Full Year', 'Custom Range'], key="loc_daterange")

    with col2:
        if date_range == 'Year to Date':
            # Multi-select for YTD comparison - default to all years
            selected_years = st.multiselect("Compare Years", [str(y) for y in years], default=[str(y) for y in years], key="loc_years_multi")
        else:
            selected_year = st.selectbox("Year", ['All Years'] + [str(y) for y in years], key="loc_year")
            selected_years = []

    # Custom date range inputs
    if date_range == 'Custom Range':
        with col3:
            start_date = st.date_input("Start", value=loc_df['date'].min().date(), key="loc_start")
        with col4:
            end_date = st.date_input("End", value=loc_df['date'].max().date(), key="loc_end")

    # Apply filters
    filtered_df = loc_df.copy()

    # Handle YTD multi-year comparison
    ytd_comparison_mode = date_range == 'Year to Date' and len(selected_years) > 1

    if date_range == 'Year to Date':
        # Filter to selected years, using week-based comparison (Saturday to Saturday)
        if selected_years:
            year_list = [int(y) for y in selected_years]
            filtered_df = filtered_df[filtered_df['year'].isin(year_list)]
        # Filter to YTD by week number and day of week for apples-to-apples comparison
        filtered_df = filter_ytd_same_dow(filtered_df)
    else:
        # Year filter for non-YTD modes
        if selected_year != 'All Years':
            filtered_df = filtered_df[filtered_df['year'] == int(selected_year)]

        # Date range filter
        if date_range == 'Full Season (May-Nov)':
            filtered_df = filtered_df[filtered_df['month'].isin([5, 6, 7, 8, 9, 10, 11])]
        elif date_range == 'Custom Range':
            filtered_df = filtered_df[
                (filtered_df['date'].dt.date >= start_date) &
                (filtered_df['date'].dt.date <= end_date)
            ]

    # Apply attendance adjustment to prior years (if enabled)
    filtered_df = apply_attendance_adjustment(filtered_df, value_cols=['gross_sales'])

    loc_df = filtered_df

    # KPIs - show year comparison if both years selected
    if ytd_comparison_mode and len(selected_years) == 2:
        year1, year2 = sorted([int(y) for y in selected_years])
        sales_y1 = loc_df[loc_df['year'] == year1]['gross_sales'].sum()
        sales_y2 = loc_df[loc_df['year'] == year2]['gross_sales'].sum()
        change_dollars = sales_y2 - sales_y1
        change_pct = ((sales_y2 - sales_y1) / sales_y1 * 100) if sales_y1 > 0 else 0
        change_sign = "+" if change_dollars >= 0 else ""

        cols = st.columns(4)
        with cols[0]:
            render_kpi_card(f"{year1} Sales", f"${sales_y1:,.0f}")
        with cols[1]:
            render_kpi_card(f"{year2} Sales", f"${sales_y2:,.0f}")
        with cols[2]:
            render_kpi_card("$ Change", f"{change_sign}${change_dollars:,.0f}")
        with cols[3]:
            render_kpi_card("% Change", f"{change_sign}{change_pct:.1f}%")
    else:
        # Standard single-period KPIs
        total_sales = loc_df['gross_sales'].sum()
        operating_days = loc_df['date'].dt.date.nunique()
        num_locations = loc_df['location'].nunique()
        daily_avg = total_sales / operating_days if operating_days > 0 else 0

        cols = st.columns(4)
        with cols[0]:
            render_kpi_card("Total Sales", f"${total_sales:,.0f}")
        with cols[1]:
            render_kpi_card("Daily Average", f"${daily_avg:,.0f}")
        with cols[2]:
            render_kpi_card("Operating Days", f"{operating_days}")
        with cols[3]:
            render_kpi_card("Locations", f"{num_locations}")

    render_section_divider()

    # Sales by location table
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Sales by Location")

    # Build table based on mode
    if ytd_comparison_mode:
        # Create pivot table with separate columns for each year
        pivot_data = loc_df.groupby(['location', 'year'])['gross_sales'].sum().unstack(fill_value=0)
        pivot_data.columns = [f'Sales {int(y)}' for y in pivot_data.columns]
        pivot_data = pivot_data.reset_index()
        pivot_data.columns = ['Location'] + list(pivot_data.columns[1:])

        # Calculate total for sorting
        sales_cols = [c for c in pivot_data.columns if c.startswith('Sales')]
        pivot_data['_total'] = pivot_data[sales_cols].sum(axis=1)
        pivot_data = pivot_data.sort_values('_total', ascending=False)
        pivot_data = pivot_data.drop(columns=['_total'])

        # Calculate YoY change if we have 2 years
        if len(sales_cols) == 2:
            col1, col2 = sales_cols[0], sales_cols[1]
            pivot_data['Change'] = pivot_data[col2] - pivot_data[col1]
            pivot_data['Change %'] = ((pivot_data[col2] - pivot_data[col1]) / pivot_data[col1].replace(0, float('nan')) * 100).fillna(0)

        location_summary = pivot_data
    else:
        # Standard single-period view
        location_summary = loc_df.groupby('location').agg({
            'gross_sales': 'sum',
            'date': 'nunique'
        }).reset_index()
        location_summary.columns = ['Location', 'Total Sales', 'Days']
        location_summary['Daily Avg'] = location_summary['Total Sales'] / location_summary['Days']
        location_summary = location_summary.sort_values('Total Sales', ascending=False)

    # Export button
    col_space, col_excel = st.columns([5, 1])
    with col_excel:
        excel_buffer = io.BytesIO()
        location_summary.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        st.download_button("Export Excel", excel_buffer, "location_sales.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    # Display with conditional formatting for Change columns
    if 'Change' in location_summary.columns:
        # YTD comparison mode - use styled dataframe
        sales_cols = [c for c in location_summary.columns if c.startswith('Sales')]
        money_cols = sales_cols + ['Change']

        styled_df = style_dataframe_with_changes(
            location_summary,
            money_cols=money_cols,
            pct_cols=['Change %'] if 'Change %' in location_summary.columns else []
        )
        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=400)
    else:
        # Standard view - use column_config
        col_config = {}
        for col in location_summary.columns:
            if col == 'Location':
                continue
            elif col == 'Days':
                col_config[col] = st.column_config.NumberColumn(col, format="%,d")
            elif 'Sales' in col or 'Avg' in col:
                col_config[col] = st.column_config.NumberColumn(col, format="$%,.0f")

        st.dataframe(location_summary, column_config=col_config, use_container_width=True, hide_index=True, height=400)
    st.markdown('</div>', unsafe_allow_html=True)

    render_section_divider()

    # ===================
    # LOCATION CUMULATIVE TREND
    # ===================
    st.markdown('<div class="card">', unsafe_allow_html=True)
    render_card_header("Location Season Trend")

    # Get list of locations
    locations = sorted(loc_df['location'].unique())

    # Location selector
    col1, col2 = st.columns([2, 3])
    with col1:
        selected_location = st.selectbox("Select Location", ["All Locations"] + locations, key="loc_trend_select")

    # Filter data for selected location
    if selected_location == "All Locations":
        trend_df = loc_df.groupby(['date', 'year'])['gross_sales'].sum().reset_index()
    else:
        trend_df = loc_df[loc_df['location'] == selected_location].copy()

    # Get years in the data
    trend_years = sorted(trend_df['year'].unique())

    # Create cumulative data for each year
    fig = go.Figure()

    # Reference year for alignment (use 2000 so all years align on same x-axis)
    REFERENCE_YEAR = 2000

    year_colors = {
        trend_years[0] if len(trend_years) > 0 else 2025: '#3b82f6',  # Blue
        trend_years[1] if len(trend_years) > 1 else 2026: '#22c55e',  # Green
    }

    cumulative_data = {}

    # Get current year for day-of-week alignment
    current_year = datetime.now().year

    def get_day_offset(year):
        """Days to add to align day-of-week with current year (same as filter_ytd_same_dow)."""
        offset = 0
        for y in range(year, current_year):
            if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
                offset += 2
            else:
                offset += 1
        return offset % 7

    for year in trend_years:
        year_data = trend_df[trend_df['year'] == year].copy()
        year_data = year_data.sort_values('date')

        # Aggregate by date
        daily = year_data.groupby(year_data['date'].dt.date)['gross_sales'].sum().reset_index()
        daily.columns = ['date', 'sales']
        daily['cumulative'] = daily['sales'].cumsum()

        # For past years, apply day offset to align with current year's day-of-week
        # e.g., 2025 Aug 23 (Sat) aligns with 2026 Aug 22 (Sat) -> subtract 1 day from 2025
        if year < current_year:
            offset = get_day_offset(int(year))
            # Shift the aligned date back by offset days so same DOW aligns
            daily['aligned_date'] = daily['date'].apply(
                lambda d: datetime(REFERENCE_YEAR, d.month, d.day) - timedelta(days=offset)
            )
        else:
            daily['aligned_date'] = daily['date'].apply(
                lambda d: datetime(REFERENCE_YEAR, d.month, d.day)
            )

        cumulative_data[year] = daily

        color = year_colors.get(year, '#9ca3af')

        fig.add_trace(go.Scatter(
            x=daily['aligned_date'],
            y=daily['cumulative'],
            mode='lines',
            name=str(int(year)),
            line=dict(color=color, width=2.5),
            hovertemplate=f'{int(year)}: $%{{y:,.0f}}<extra></extra>'
        ))

    # If we have exactly 2 years, find and annotate the largest discrepancies
    if len(trend_years) == 2:
        year1, year2 = trend_years[0], trend_years[1]
        df1 = cumulative_data[year1].set_index('aligned_date')
        df2 = cumulative_data[year2].set_index('aligned_date')

        # Join on aligned date
        merged = df1[['cumulative']].join(df2[['cumulative']], lsuffix='_y1', rsuffix='_y2', how='inner')

        if len(merged) > 0:
            # Calculate % difference at each point
            merged['pct_diff'] = ((merged['cumulative_y2'] - merged['cumulative_y1']) / merged['cumulative_y1'] * 100).fillna(0)

            # Only consider dates after June 10 for max/min (small sample size before then)
            june_10_cutoff = datetime(REFERENCE_YEAR, 6, 10)
            merged_after_june = merged[merged.index >= june_10_cutoff]

            # Find max positive and negative discrepancy (only after June 10)
            if len(merged_after_june) > 0:
                max_pos_idx = merged_after_june['pct_diff'].idxmax()
                max_neg_idx = merged_after_june['pct_diff'].idxmin()
                max_pos_pct = merged_after_june.loc[max_pos_idx, 'pct_diff']
                max_neg_pct = merged_after_june.loc[max_neg_idx, 'pct_diff']
            else:
                max_pos_idx = merged['pct_diff'].idxmax()
                max_neg_idx = merged['pct_diff'].idxmin()
                max_pos_pct = merged.loc[max_pos_idx, 'pct_diff']
                max_neg_pct = merged.loc[max_neg_idx, 'pct_diff']

            # Add annotations for these points
            if max_pos_pct > 0:
                fig.add_annotation(
                    x=max_pos_idx,
                    y=merged.loc[max_pos_idx, 'cumulative_y2'],
                    text=f"+{max_pos_pct:.1f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowcolor='#22c55e',
                    font=dict(color='#22c55e', size=12, weight='bold'),
                    bgcolor='rgba(34, 197, 94, 0.1)',
                    bordercolor='#22c55e',
                    borderwidth=1,
                    borderpad=4
                )

            if max_neg_pct < 0:
                fig.add_annotation(
                    x=max_neg_idx,
                    y=merged.loc[max_neg_idx, 'cumulative_y2'],
                    text=f"{max_neg_pct:.1f}%",
                    showarrow=True,
                    arrowhead=2,
                    arrowsize=1,
                    arrowcolor='#ef4444',
                    font=dict(color='#ef4444', size=12, weight='bold'),
                    bgcolor='rgba(239, 68, 68, 0.1)',
                    bordercolor='#ef4444',
                    borderwidth=1,
                    borderpad=4
                )

    layout = get_chart_layout(350)
    layout['xaxis']['tickformat'] = '%b %d'
    layout['legend'] = dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1, font=dict(color='#e5e7eb', size=13))
    layout['margin'] = dict(l=10, r=10, t=40, b=30)
    layout['hovermode'] = 'x unified'
    fig.update_layout(**layout)

    st.plotly_chart(fig, use_container_width=True)

    # Show summary for 2-year comparison
    if len(trend_years) == 2 and len(merged) > 0:
        final_y1 = merged['cumulative_y1'].iloc[-1]
        final_y2 = merged['cumulative_y2'].iloc[-1]
        final_diff = ((final_y2 - final_y1) / final_y1 * 100) if final_y1 > 0 else 0
        diff_color = "#22c55e" if final_diff >= 0 else "#ef4444"
        diff_sign = "+" if final_diff >= 0 else ""

        st.markdown(f"""
            <div style="color: #9ca3af; font-size: 14px; margin-top: 8px;">
                <span style="color: #6b7280;">Current YTD:</span>
                <span style="color: {diff_color}; font-weight: 600; margin-left: 8px;">
                    {diff_sign}{final_diff:.1f}% vs {int(year1)}
                </span>
                <span style="color: #6b7280; margin-left: 16px;">
                    (Max gain: +{max_pos_pct:.1f}% · Max gap: {max_neg_pct:.1f}%)
                </span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def process_location_uploads(uploaded_files):
    """Process uploaded location files."""
    progress = st.progress(0, text="Processing files...")

    processed = 0
    errors = []
    all_data = []
    dates_processed = []

    for i, f in enumerate(uploaded_files):
        progress.progress((i + 1) / len(uploaded_files), text=f"Processing {f.name}...")

        file_bytes = f.read()
        operating_date, df, error = process_location_file(file_bytes, f.name)

        if error:
            errors.append(f"{f.name}: {error}")
        elif operating_date is not None and df is not None and len(df) > 0:
            all_data.append(df)
            dates_processed.append(operating_date.strftime('%Y-%m-%d'))
            processed += 1

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        merge_location_data(combined_df)

        progress.empty()
        st.success(f"✅ Processed {processed} file(s) successfully!")
        if dates_processed:
            st.markdown(f"<p style='color: #9ca3af; font-size: 14px;'>Dates added/updated: {', '.join(sorted(dates_processed))}</p>", unsafe_allow_html=True)

        if errors:
            with st.expander("View errors"):
                for err in errors:
                    st.text(err)

        st.info("🔄 Refresh the page to see updated data.")
    else:
        progress.empty()
        if errors:
            st.error("No files could be processed.")
            for err in errors:
                st.text(err)


# =============================================================================
# ATTENDANCE ADJUSTMENT
# =============================================================================

def is_admin_mode():
    """Check if admin mode is enabled via URL parameter."""
    # Access via ?admin=clp in URL to enable admin features (to SET the percentage)
    try:
        params = st.query_params
        admin_val = params.get("admin", "")
        # Handle both string and list returns from query_params
        if isinstance(admin_val, list):
            admin_val = admin_val[0] if admin_val else ""
        return str(admin_val).lower() == "clp"
    except:
        return False


def load_attendance_adjustment_pct():
    """Load the admin-set attendance adjustment percentage from database."""
    try:
        if table_exists('app_settings'):
            result = read_sql("SELECT value FROM app_settings WHERE key = 'attendance_adj_pct'")
            if len(result) > 0:
                return float(result['value'].iloc[0])
    except:
        pass
    return 0.0


def save_attendance_adjustment_pct(pct):
    """Save the attendance adjustment percentage to database (admin only)."""
    try:
        # Create settings table if not exists
        if is_cloud_mode():
            execute_sql("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key VARCHAR(100) PRIMARY KEY,
                    value TEXT
                )
            """)
            # Upsert the value
            execute_sql("""
                INSERT INTO app_settings (key, value) VALUES ('attendance_adj_pct', :val)
                ON CONFLICT (key) DO UPDATE SET value = :val
            """, {"val": str(pct)})
        else:
            execute_sql("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            # SQLite upsert
            execute_sql("INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                       ('attendance_adj_pct', str(pct)))
    except Exception as e:
        st.error(f"Could not save setting: {e}")


def get_attendance_adjustment():
    """Get the current attendance adjustment factor."""
    if 'attendance_adj_enabled' not in st.session_state:
        st.session_state.attendance_adj_enabled = True  # Default to ON

    # Load the admin-set percentage from database (cached in session)
    if 'attendance_adj_pct' not in st.session_state:
        st.session_state.attendance_adj_pct = load_attendance_adjustment_pct()

    if st.session_state.attendance_adj_enabled:
        return st.session_state.attendance_adj_pct
    return 0.0


def apply_attendance_adjustment(df, year_col='year', value_cols=None):
    """
    Apply attendance adjustment to prior year data.
    If attendance is DOWN x% in current year, reduce prior year values by x%.
    This normalizes comparisons to be "per-attendee" equivalent.

    Args:
        df: DataFrame to adjust
        year_col: Column containing year
        value_cols: List of columns to adjust (e.g., ['total_price', 'total_qty', 'gross_sales'])

    Returns:
        Adjusted DataFrame
    """
    adj_pct = get_attendance_adjustment()
    if adj_pct == 0:
        return df

    df = df.copy()
    current_year = datetime.now().year

    # Apply adjustment factor to prior years
    # If attendance is down 10% (adj_pct = -10), multiply prior year by 0.9
    adjustment_factor = 1 + (adj_pct / 100)

    if value_cols is None:
        value_cols = ['total_price', 'total_qty', 'gross_sales']

    for col in value_cols:
        if col in df.columns:
            # Only adjust prior years, not current year
            prior_year_mask = df[year_col] < current_year
            df.loc[prior_year_mask, col] = df.loc[prior_year_mask, col] * adjustment_factor

    return df


# =============================================================================
# TAB: SEASON RACE (Animated YoY Comparison)
# =============================================================================

def render_season_race(df):
    """Render animated season race visualization - like real-time trading charts."""

    st.markdown("""
        <style>
        .race-container {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
        .race-ticker {
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', monospace;
            font-size: 42px;
            font-weight: 700;
            letter-spacing: -1px;
        }
        .race-label {
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }
        .race-change-positive {
            color: #22c55e;
            font-size: 24px;
            font-weight: 600;
        }
        .race-change-negative {
            color: #ef4444;
            font-size: 24px;
            font-weight: 600;
        }
        .race-momentum {
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            display: inline-block;
        }
        .momentum-accelerating {
            background: rgba(34, 197, 94, 0.15);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .momentum-decelerating {
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .momentum-stable {
            background: rgba(148, 163, 184, 0.15);
            color: #94a3b8;
            border: 1px solid rgba(148, 163, 184, 0.3);
        }
        .race-date-display {
            font-family: 'SF Mono', monospace;
            font-size: 18px;
            color: #3b82f6;
            background: rgba(59, 130, 246, 0.1);
            padding: 8px 16px;
            border-radius: 8px;
            border: 1px solid rgba(59, 130, 246, 0.2);
        }
        .deviation-alert {
            background: linear-gradient(90deg, rgba(234, 179, 8, 0.1) 0%, transparent 100%);
            border-left: 3px solid #eab308;
            padding: 12px 16px;
            margin: 8px 0;
            border-radius: 0 8px 8px 0;
        }
        .deviation-alert-positive {
            background: linear-gradient(90deg, rgba(34, 197, 94, 0.1) 0%, transparent 100%);
            border-left-color: #22c55e;
        }
        .deviation-alert-negative {
            background: linear-gradient(90deg, rgba(239, 68, 68, 0.1) 0%, transparent 100%);
            border-left-color: #ef4444;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="section-header">
            <div class="section-title">Season Race</div>
            <div class="section-subtitle">Watch the season unfold with animated YoY comparison</div>
        </div>
    """, unsafe_allow_html=True)

    # Get available years
    years = sorted(df['year'].dropna().unique())
    if len(years) < 2:
        st.info("Need at least 2 years of data for comparison.")
        return

    # Compact controls row
    col1, col2, col3, col4 = st.columns([1, 2.5, 0.6, 0.6])

    with col1:
        compare_type = st.selectbox("Compare", ["All Sales", "Category", "Location", "Items"], key="race_compare_type", label_visibility="collapsed")

    with col2:
        if compare_type == "Category":
            categories = sorted([c for c in df['category'].unique() if c and pd.notna(c)])
            selected_entities = st.multiselect("Categories", categories, default=[categories[0]] if categories else [], key="race_categories", label_visibility="collapsed", placeholder="Select categories...")
        elif compare_type == "Location":
            try:
                loc_df = read_sql("SELECT DISTINCT location FROM location_sales")
                locations = sorted(loc_df['location'].tolist())
            except:
                locations = []
            if locations:
                selected_entities = st.multiselect("Locations", locations, default=[locations[0]] if locations else [], key="race_locations", label_visibility="collapsed", placeholder="Select locations...")
            else:
                st.caption("No location data")
                selected_entities = []
        elif compare_type == "Items":
            items = sorted([i for i in df['plu_name'].unique() if i and pd.notna(i)])
            selected_entities = st.multiselect("Items", items, default=[], key="race_items", label_visibility="collapsed", placeholder="Search & select items...")
        else:
            selected_entities = ["All"]

    with col3:
        year1 = st.selectbox("", [int(y) for y in years[:-1]], index=len(years)-2, key="race_year1", label_visibility="collapsed")

    with col4:
        year2_options = [int(y) for y in years if y > year1]
        if year2_options:
            year2 = st.selectbox("", year2_options, index=len(year2_options)-1, key="race_year2", label_visibility="collapsed")
        else:
            year2 = int(years[-1])
            st.selectbox("", [year2], key="race_year2", label_visibility="collapsed")

    # Validate selection
    if compare_type != "All Sales" and not selected_entities:
        st.info(f"Select at least one {compare_type.lower().rstrip('s')} to compare.")
        return

    # Prepare data based on comparison type
    if compare_type == "Location" and selected_entities:
        try:
            loc_data = read_sql("SELECT date, location, gross_sales FROM location_sales")
            loc_data['date'] = pd.to_datetime(loc_data['date'])
            loc_data['year'] = loc_data['date'].dt.year
            race_df = loc_data[loc_data['location'].isin(selected_entities)].copy()
            value_col = 'gross_sales'
        except:
            st.error("Could not load location data")
            return
    elif compare_type == "Category" and selected_entities:
        race_df = df[df['category'].isin(selected_entities)].copy()
        value_col = 'total_price'
    elif compare_type == "Items" and selected_entities:
        race_df = df[df['plu_name'].isin(selected_entities)].copy()
        value_col = 'total_price'
    else:
        race_df = df.copy()
        value_col = 'total_price'

    # Apply attendance adjustment
    if value_col == 'total_price':
        race_df = apply_attendance_adjustment(race_df, value_cols=['total_price'])
    elif value_col == 'gross_sales':
        race_df = apply_attendance_adjustment(race_df, value_cols=['gross_sales'])

    # Filter to selected years
    race_df = race_df[race_df['year'].isin([year1, year2])]

    if len(race_df) == 0:
        st.warning("No data available for selected filters.")
        return

    # Aggregate daily data for each year
    daily_y1 = race_df[race_df['year'] == year1].groupby(race_df[race_df['year'] == year1]['date'].dt.date)[value_col].sum().reset_index()
    daily_y2 = race_df[race_df['year'] == year2].groupby(race_df[race_df['year'] == year2]['date'].dt.date)[value_col].sum().reset_index()

    daily_y1.columns = ['date', 'sales']
    daily_y2.columns = ['date', 'sales']

    daily_y1['date'] = pd.to_datetime(daily_y1['date'])
    daily_y2['date'] = pd.to_datetime(daily_y2['date'])

    # Filter to May 16th onwards (opening day)
    daily_y1 = daily_y1[(daily_y1['date'].dt.month > 5) | ((daily_y1['date'].dt.month == 5) & (daily_y1['date'].dt.day >= 16))]
    daily_y2 = daily_y2[(daily_y2['date'].dt.month > 5) | ((daily_y2['date'].dt.month == 5) & (daily_y2['date'].dt.day >= 16))]

    daily_y1 = daily_y1.sort_values('date')
    daily_y2 = daily_y2.sort_values('date')

    # Calculate cumulative (starting from May 1)
    daily_y1['cumulative'] = daily_y1['sales'].cumsum()
    daily_y2['cumulative'] = daily_y2['sales'].cumsum()

    # Align dates using day-of-week matching
    REFERENCE_YEAR = 2000
    current_year = datetime.now().year

    def get_day_offset(year):
        offset = 0
        for y in range(year, current_year):
            if (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0):
                offset += 2
            else:
                offset += 1
        return offset % 7

    offset_y1 = get_day_offset(year1)

    daily_y1['aligned_date'] = daily_y1['date'].apply(
        lambda d: datetime(REFERENCE_YEAR, d.month, d.day) - timedelta(days=offset_y1)
    )
    daily_y2['aligned_date'] = daily_y2['date'].apply(
        lambda d: datetime(REFERENCE_YEAR, d.month, d.day)
    )

    # Merge on aligned date (include daily sales for hover)
    merged = daily_y1[['aligned_date', 'sales', 'cumulative']].merge(
        daily_y2[['aligned_date', 'sales', 'cumulative']],
        on='aligned_date',
        how='inner',
        suffixes=('_y1', '_y2')
    ).sort_values('aligned_date')

    # Filter to start from May 16th (opening day)
    may_16th = datetime(REFERENCE_YEAR, 5, 16)
    merged = merged[merged['aligned_date'] >= may_16th].reset_index(drop=True)

    if len(merged) == 0:
        st.warning("No overlapping dates between the two years.")
        return

    # Calculate metrics at each point
    merged['diff'] = merged['cumulative_y2'] - merged['cumulative_y1']
    merged['pct_diff'] = ((merged['cumulative_y2'] - merged['cumulative_y1']) / merged['cumulative_y1'] * 100).fillna(0)
    merged['pct_diff_change'] = merged['pct_diff'].diff().fillna(0)  # Momentum

    # Daily sales comparison
    merged['daily_diff'] = merged['sales_y2'] - merged['sales_y1']
    merged['daily_pct'] = ((merged['sales_y2'] - merged['sales_y1']) / merged['sales_y1'].replace(0, float('nan')) * 100).fillna(0)

    # Get final values for summary display
    final_row = merged.iloc[-1]
    final_y1 = final_row['cumulative_y1']
    final_y2 = final_row['cumulative_y2']
    final_diff = final_row['diff']
    final_pct = final_row['pct_diff']

    # Get today's sales (last row)
    today_y1 = final_row['sales_y1']
    today_y2 = final_row['sales_y2']
    today_pct = final_row['daily_pct']

    # Calculate recent momentum
    recent_momentum = merged['pct_diff_change'].tail(7).mean() if len(merged) >= 7 else 0

    # ========================================
    # FOMO-STYLE TOP STATS BAR
    # ========================================
    st.markdown("""
        <div style="display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px;">
    """, unsafe_allow_html=True)

    # Stat cards in a row
    stats_data = [
        (f"{year2} Total", f"${final_y2:,.0f}", "#10b981", None),
        ("YoY Change", f"{'+' if final_pct >= 0 else ''}{final_pct:.1f}%", "#22c55e" if final_pct >= 0 else "#ef4444", f"${'+' if final_diff >= 0 else ''}{final_diff:,.0f}"),
        ("Today's Sales", f"${today_y2:,.0f}", "#3b82f6", f"{'+' if today_pct >= 0 else ''}{today_pct:.1f}% vs LY"),
        ("Momentum", f"{'+' if recent_momentum >= 0 else ''}{recent_momentum:.2f}%/day", "#22c55e" if recent_momentum >= 0 else "#ef4444", "7-day avg"),
        (f"{year1} Total", f"${final_y1:,.0f}", "#6b7280", None),
    ]

    stat_cols = st.columns(5)
    for i, (label, value, color, subtitle) in enumerate(stats_data):
        with stat_cols[i]:
            subtitle_html = f'<div style="color: #64748b; font-size: 11px; margin-top: 2px;">{subtitle}</div>' if subtitle else ''
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
                            border: 1px solid rgba(71, 85, 105, 0.3); border-radius: 12px; padding: 12px 16px; text-align: center;">
                    <div style="color: #9ca3af; font-size: 10px; text-transform: uppercase; letter-spacing: 1px;">{label}</div>
                    <div style="color: {color}; font-size: 20px; font-weight: 700; margin-top: 4px; font-family: 'SF Mono', monospace;">{value}</div>
                    {subtitle_html}
                </div>
            """, unsafe_allow_html=True)

    # ========================================
    # TALE OF THE TAPE (Compact inline comparison)
    # ========================================
    avg_daily_y1 = merged['sales_y1'].mean()
    avg_daily_y2 = merged['sales_y2'].mean()
    best_day_y1 = merged['sales_y1'].max()
    best_day_y2 = merged['sales_y2'].max()
    days_winning_y2 = (merged['sales_y2'] > merged['sales_y1']).sum()
    days_winning_y1 = (merged['sales_y1'] > merged['sales_y2']).sum()

    st.markdown(f"""
        <div style="display: flex; justify-content: center; gap: 32px; margin: 12px 0 16px 0; flex-wrap: wrap;">
            <div style="text-align: center;">
                <div style="color: #6b7280; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;">Avg Daily</div>
                <div style="margin-top: 4px;">
                    <span style="color: #3b82f6; font-size: 14px; font-weight: 600;">${avg_daily_y1:,.0f}</span>
                    <span style="color: #4b5563; margin: 0 6px;">vs</span>
                    <span style="color: #10b981; font-size: 14px; font-weight: 600;">${avg_daily_y2:,.0f}</span>
                </div>
            </div>
            <div style="text-align: center;">
                <div style="color: #6b7280; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;">Best Day</div>
                <div style="margin-top: 4px;">
                    <span style="color: #3b82f6; font-size: 14px; font-weight: 600;">${best_day_y1:,.0f}</span>
                    <span style="color: #4b5563; margin: 0 6px;">vs</span>
                    <span style="color: #10b981; font-size: 14px; font-weight: 600;">${best_day_y2:,.0f}</span>
                </div>
            </div>
            <div style="text-align: center;">
                <div style="color: #6b7280; font-size: 10px; text-transform: uppercase; letter-spacing: 0.5px;">Days Won</div>
                <div style="margin-top: 4px;">
                    <span style="color: #3b82f6; font-size: 14px; font-weight: 600;">{days_winning_y1}</span>
                    <span style="color: #4b5563; margin: 0 6px;">vs</span>
                    <span style="color: #10b981; font-size: 14px; font-weight: 600;">{days_winning_y2}</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Create animated race chart using Plotly frames (runs in browser - no server lag)
    # Trading app style: glowing lines, gradient fills, smooth curves
    fig = go.Figure()

    # Trace 0: Year 1 glow (outer glow effect - wider, transparent)
    fig.add_trace(go.Scatter(
        x=[merged['aligned_date'].iloc[0]],
        y=[merged['cumulative_y1'].iloc[0]],
        mode='lines',
        name='',
        line=dict(color='rgba(59, 130, 246, 0.3)', width=12, shape='spline', smoothing=0.8),
        hoverinfo='skip',
        showlegend=False
    ))

    # Trace 1: Year 1 main line (hover shows daily comparison)
    fig.add_trace(go.Scatter(
        x=[merged['aligned_date'].iloc[0]],
        y=[merged['cumulative_y1'].iloc[0]],
        mode='lines',
        name=str(year1),
        line=dict(color='#3b82f6', width=4, shape='spline', smoothing=0.8),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.12)',
        hoverinfo='skip'
    ))

    # Trace 2: Year 1 moving dot head
    fig.add_trace(go.Scatter(
        x=[merged['aligned_date'].iloc[0]],
        y=[merged['cumulative_y1'].iloc[0]],
        mode='markers',
        name='',
        marker=dict(color='#3b82f6', size=14, symbol='circle',
                   line=dict(color='white', width=2)),
        hoverinfo='skip',
        showlegend=False
    ))

    # Trace 3: Year 2 glow (outer glow effect)
    fig.add_trace(go.Scatter(
        x=[merged['aligned_date'].iloc[0]],
        y=[merged['cumulative_y2'].iloc[0]],
        mode='lines',
        name='',
        line=dict(color='rgba(16, 185, 129, 0.3)', width=12, shape='spline', smoothing=0.8),
        hoverinfo='skip',
        showlegend=False
    ))

    # Trace 4: Year 2 main line
    fig.add_trace(go.Scatter(
        x=[merged['aligned_date'].iloc[0]],
        y=[merged['cumulative_y2'].iloc[0]],
        mode='lines',
        name=str(year2),
        line=dict(color='#10b981', width=4, shape='spline', smoothing=0.8),
        fill='tozeroy',
        fillcolor='rgba(16, 185, 129, 0.12)',
        hoverinfo='skip'
    ))

    # Trace 5: Year 2 moving dot head
    fig.add_trace(go.Scatter(
        x=[merged['aligned_date'].iloc[0]],
        y=[merged['cumulative_y2'].iloc[0]],
        mode='markers',
        name='',
        marker=dict(color='#10b981', size=14, symbol='circle',
                   line=dict(color='white', width=2)),
        hoverinfo='skip',
        showlegend=False
    ))

    # Trace 6: Invisible hover trace for daily sales comparison
    # Build custom hover text for each date
    hover_texts = []
    for _, row in merged.iterrows():
        daily_change_pct = row['daily_pct']
        daily_change_sign = "+" if daily_change_pct >= 0 else ""
        daily_change_color = "🟢" if daily_change_pct >= 0 else "🔴"

        hover_texts.append(
            f"<b>{row['aligned_date'].strftime('%b %d')}</b><br><br>"
            f"<b>Daily Sales</b><br>"
            f"{year1}: ${row['sales_y1']:,.0f}<br>"
            f"{year2}: ${row['sales_y2']:,.0f}<br>"
            f"{daily_change_color} {daily_change_sign}{daily_change_pct:.1f}%<br><br>"
            f"<b>Cumulative</b><br>"
            f"{year1}: ${row['cumulative_y1']:,.0f}<br>"
            f"{year2}: ${row['cumulative_y2']:,.0f}<br>"
            f"Gap: {'+' if row['pct_diff'] >= 0 else ''}{row['pct_diff']:.1f}%"
        )

    fig.add_trace(go.Scatter(
        x=merged['aligned_date'],
        y=merged['cumulative_y2'],
        mode='lines',
        name='',
        line=dict(color='rgba(0,0,0,0)', width=0),
        hovertemplate='%{text}<extra></extra>',
        text=hover_texts,
        showlegend=False
    ))

    # Build animation frames with glow + moving dots
    step = max(1, len(merged) // 100)  # ~100 frames for smoother animation
    frame_indices = list(range(0, len(merged), step)) + [len(merged) - 1]
    frame_indices = sorted(set(frame_indices))

    frames = []
    for i in frame_indices:
        frame_data = merged.iloc[:i + 1]
        current_row = merged.iloc[i]

        frames.append(go.Frame(
            data=[
                # Year 1 glow
                go.Scatter(
                    x=frame_data['aligned_date'],
                    y=frame_data['cumulative_y1'],
                    line=dict(color='rgba(59, 130, 246, 0.3)', width=12, shape='spline', smoothing=0.8)
                ),
                # Year 1 main line
                go.Scatter(
                    x=frame_data['aligned_date'],
                    y=frame_data['cumulative_y1'],
                    line=dict(color='#3b82f6', width=4, shape='spline', smoothing=0.8),
                    fill='tozeroy',
                    fillcolor='rgba(59, 130, 246, 0.12)'
                ),
                # Year 1 dot head
                go.Scatter(
                    x=[current_row['aligned_date']],
                    y=[current_row['cumulative_y1']],
                    marker=dict(color='#3b82f6', size=14, symbol='circle',
                               line=dict(color='white', width=2))
                ),
                # Year 2 glow
                go.Scatter(
                    x=frame_data['aligned_date'],
                    y=frame_data['cumulative_y2'],
                    line=dict(color='rgba(16, 185, 129, 0.3)', width=12, shape='spline', smoothing=0.8)
                ),
                # Year 2 main line
                go.Scatter(
                    x=frame_data['aligned_date'],
                    y=frame_data['cumulative_y2'],
                    line=dict(color='#10b981', width=4, shape='spline', smoothing=0.8),
                    fill='tozeroy',
                    fillcolor='rgba(16, 185, 129, 0.12)'
                ),
                # Year 2 dot head
                go.Scatter(
                    x=[current_row['aligned_date']],
                    y=[current_row['cumulative_y2']],
                    marker=dict(color='#10b981', size=14, symbol='circle',
                               line=dict(color='white', width=2))
                ),
            ],
            name=str(i)
        ))

    fig.frames = frames

    # July 1st cutoff for meaningful stats
    july_1st = datetime(REFERENCE_YEAR, 7, 1)

    # Add vertical line at July 1st to mark "meaningful data" boundary
    fig.add_vline(
        x=july_1st,
        line=dict(color='rgba(148, 163, 184, 0.4)', width=1, dash='dash'),
        annotation_text="Jul 1",
        annotation_position="top",
        annotation_font=dict(color='#64748b', size=10)
    )

    # Calculate momentum shifts (diverging = gap widening, converging = gap narrowing)
    merged['abs_swing'] = merged['pct_diff_change'].abs()
    merged['is_diverging'] = merged['pct_diff_change'].abs() > 0  # Gap changing

    # Split data: before and after July 1
    pre_july = merged[merged['aligned_date'] < july_1st]
    post_july = merged[merged['aligned_date'] >= july_1st]

    # Find key moments AFTER July 1 only (for lead/gap stats)
    if len(post_july) > 0:
        best_lead_idx = post_july['pct_diff'].idxmax()
        worst_gap_idx = post_july['pct_diff'].idxmin()
        best_lead_row = post_july.loc[best_lead_idx]
        worst_gap_row = post_july.loc[worst_gap_idx]

        # Mark best lead point with a subtle dot
        fig.add_trace(go.Scatter(
            x=[best_lead_row['aligned_date']],
            y=[best_lead_row['cumulative_y2']],
            mode='markers+text',
            marker=dict(color='#22c55e', size=10, symbol='circle'),
            text=[f"+{best_lead_row['pct_diff']:.1f}%"],
            textposition='top center',
            textfont=dict(color='#22c55e', size=11),
            showlegend=False,
            hoverinfo='skip'
        ))

        # Mark worst gap point
        fig.add_trace(go.Scatter(
            x=[worst_gap_row['aligned_date']],
            y=[worst_gap_row['cumulative_y2']],
            mode='markers+text',
            marker=dict(color='#ef4444', size=10, symbol='circle'),
            text=[f"{worst_gap_row['pct_diff']:.1f}%"],
            textposition='bottom center',
            textfont=dict(color='#ef4444', size=11),
            showlegend=False,
            hoverinfo='skip'
        ))

    # Animation controls
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                showactive=False,
                y=1.15,
                x=0,
                xanchor="left",
                buttons=[
                    dict(label="▶ Play",
                         method="animate",
                         args=[None, {"frame": {"duration": 30, "redraw": True},
                                     "fromcurrent": True,
                                     "transition": {"duration": 10}}]),
                    dict(label="⏸ Pause",
                         method="animate",
                         args=[[None], {"frame": {"duration": 0, "redraw": False},
                                       "mode": "immediate",
                                       "transition": {"duration": 0}}]),
                ]
            )
        ],
        sliders=[{
            "active": len(frames) - 1,
            "yanchor": "top",
            "xanchor": "left",
            "currentvalue": {
                "prefix": "Date: ",
                "visible": True,
                "xanchor": "center",
                "font": {"size": 12, "color": "#9ca3af"}
            },
            "transition": {"duration": 0},
            "pad": {"b": 10, "t": 30},
            "len": 0.9,
            "x": 0.05,
            "y": 0,
            "steps": [
                {"args": [[str(i)], {"frame": {"duration": 0, "redraw": True},
                                     "mode": "immediate",
                                     "transition": {"duration": 0}}],
                 "label": merged.iloc[i]['aligned_date'].strftime('%b %d'),
                 "method": "animate"}
                for i in frame_indices
            ]
        }]
    )

    # Trading app style layout - dark, sleek, high contrast
    max_y = max(merged['cumulative_y1'].max(), merged['cumulative_y2'].max()) * 1.1

    # Dynamic x-axis - expand with data, add small padding
    x_min = merged['aligned_date'].min() - timedelta(days=2)
    x_max = merged['aligned_date'].max() + timedelta(days=5)  # Small padding for visibility

    # ========================================
    # MILESTONE MARKERS
    # ========================================
    # Add horizontal milestone lines at key dollar amounts
    milestone_values = [250000, 500000, 750000, 1000000, 1500000, 2000000, 2500000, 3000000]
    milestone_labels = ["$250K", "$500K", "$750K", "$1M", "$1.5M", "$2M", "$2.5M", "$3M"]

    for val, label in zip(milestone_values, milestone_labels):
        if val < max_y:  # Only show milestones within the data range
            fig.add_hline(
                y=val,
                line=dict(color='rgba(148, 163, 184, 0.25)', width=1, dash='dot'),
                annotation_text=label,
                annotation_position="left",
                annotation_font=dict(color='rgba(148, 163, 184, 0.6)', size=10)
            )

    fig.update_layout(
        plot_bgcolor='rgba(10, 10, 20, 1)',
        paper_bgcolor='rgba(10, 10, 20, 1)',
        height=480,
        xaxis=dict(
            tickformat='%b %d',
            range=[x_min, x_max],
            showgrid=True,
            gridcolor='rgba(55, 65, 81, 0.3)',
            gridwidth=1,
            tickfont=dict(color='#9ca3af', size=11),
            showline=False,
            zeroline=False
        ),
        yaxis=dict(
            range=[0, max_y],
            showgrid=True,
            gridcolor='rgba(55, 65, 81, 0.3)',
            gridwidth=1,
            tickfont=dict(color='#9ca3af', size=11),
            tickformat='$,.0f',
            showline=False,
            zeroline=False
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(color='#e5e7eb', size=14),
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(l=60, r=20, t=60, b=90),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor='rgba(30, 41, 59, 0.95)',
            font_size=13,
            font_color='#e5e7eb',
            bordercolor='rgba(59, 130, 246, 0.5)'
        )
    )

    st.plotly_chart(fig, use_container_width=True, key="race_main_chart")

    # ========================================
    # TOP PERFORMERS PANEL - Locations Only
    # ========================================
    render_section_divider()
    render_card_header("📍 Top Locations YoY")

    try:
        loc_data = read_sql("SELECT date, location, gross_sales FROM location_sales")
        loc_data['date'] = pd.to_datetime(loc_data['date'])
        loc_data['year'] = loc_data['date'].dt.year
        loc_y1 = loc_data[loc_data['year'] == year1].groupby('location')['gross_sales'].sum()
        loc_y2 = loc_data[loc_data['year'] == year2].groupby('location')['gross_sales'].sum()
        loc_yoy = ((loc_y2 - loc_y1) / loc_y1 * 100).dropna()
        loc_yoy = loc_yoy[loc_y1 > 1000]  # Minimum threshold
        top_locs = loc_yoy.nlargest(5)

        loc_cols = st.columns(5)
        for i, (loc_name, pct) in enumerate(top_locs.items()):
            with loc_cols[i]:
                display_name = loc_name[:20] + "..." if len(str(loc_name)) > 20 else loc_name
                color = "#22c55e" if pct > 0 else "#ef4444"
                sign = "+" if pct > 0 else ""
                st.markdown(f"""
                    <div style="background: rgba(30, 41, 59, 0.4); border-radius: 8px; padding: 12px; text-align: center;">
                        <div style="color: #9ca3af; font-size: 11px; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{display_name}</div>
                        <div style="color: {color}; font-size: 18px; font-weight: 700;">{sign}{pct:.0f}%</div>
                    </div>
                """, unsafe_allow_html=True)
    except:
        st.caption("No location data available")

    # Insights section - split by pre/post July 1
    render_section_divider()

    # Post-July stats (meaningful sample size)
    if len(post_july) > 0:
        render_card_header("Season Performance (After Jul 1)")

        post_july_lead = post_july['pct_diff'].max()
        post_july_gap = post_july['pct_diff'].min()
        post_july_swing = post_july['pct_diff_change'].abs().max()
        current_pct = merged['pct_diff'].iloc[-1]

        s1, s2, s3, s4 = st.columns(4)
        with s1:
            render_kpi_card("Current", f"{'+' if current_pct >= 0 else ''}{current_pct:.1f}%")
        with s2:
            render_kpi_card("Best Lead", f"+{post_july_lead:.1f}%" if post_july_lead > 0 else f"{post_july_lead:.1f}%")
        with s3:
            render_kpi_card("Worst Gap", f"{post_july_gap:.1f}%")
        with s4:
            render_kpi_card("Max Daily Swing", f"{post_july_swing:.1f}%")

    # Key momentum shifts table (3-day average momentum, after June 15)
    render_section_divider()
    render_card_header("Momentum Analysis")

    # Calculate 3-day rolling average of momentum change
    merged['momentum_3day'] = merged['pct_diff_change'].rolling(window=3, min_periods=1).mean()
    merged['momentum_7day'] = merged['pct_diff_change'].rolling(window=7, min_periods=3).mean()
    merged['abs_momentum_3day'] = merged['momentum_3day'].abs()

    # Filter to after June 15 only
    june_15th = datetime(REFERENCE_YEAR, 6, 15)
    post_june15 = merged[merged['aligned_date'] >= june_15th].copy()

    if len(post_june15) > 0:
        # Current momentum status (last 7 days)
        recent_momentum = post_june15['momentum_7day'].iloc[-1] if len(post_june15) > 0 else 0
        recent_momentum_3d = post_june15['momentum_3day'].iloc[-1] if len(post_june15) > 0 else 0

        if recent_momentum > 0.3:
            momentum_status = f"🟢 {year2} Gaining ({recent_momentum_3d:+.2f}%/day)"
            momentum_desc = f"{year2} is pulling further ahead"
        elif recent_momentum < -0.3:
            momentum_status = f"🔴 {year2} Losing ({recent_momentum_3d:+.2f}%/day)"
            momentum_desc = f"{year1} is catching up"
        else:
            momentum_status = f"⚪ Stable ({recent_momentum_3d:+.2f}%/day)"
            momentum_desc = "Gap holding steady"

        st.markdown(f"""
            <div style="background: rgba(30, 41, 59, 0.5); padding: 12px 16px; border-radius: 8px; margin-bottom: 16px;">
                <div style="font-size: 16px; font-weight: 600; color: #e5e7eb;">{momentum_status}</div>
                <div style="font-size: 13px; color: #9ca3af; margin-top: 4px;">{momentum_desc}</div>
            </div>
        """, unsafe_allow_html=True)

        # Show top 3 gaining and top 3 losing momentum days
        st.markdown('<p style="color: #9ca3af; font-size: 12px; margin: 12px 0 8px 0;">Top Momentum Shifts (after Jun 15)</p>', unsafe_allow_html=True)

        top_gaining = post_june15.nlargest(3, 'momentum_3day')[['aligned_date', 'momentum_3day', 'pct_diff']]
        top_losing = post_june15.nsmallest(3, 'momentum_3day')[['aligned_date', 'momentum_3day', 'pct_diff']]

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f'<p style="color: #22c55e; font-size: 11px; text-transform: uppercase;">🔺 {year2} Gaining Days</p>', unsafe_allow_html=True)
            if len(top_gaining) > 0:
                for _, row in top_gaining.iterrows():
                    st.markdown(f"""
                        <div style="color: #e5e7eb; font-size: 13px; padding: 4px 0;">
                            <span style="color: #6b7280;">{row['aligned_date'].strftime('%b %d')}</span>
                            <span style="color: #22c55e; margin-left: 8px;">+{row['momentum_3day']:.2f}%/day</span>
                        </div>
                    """, unsafe_allow_html=True)

        with col2:
            st.markdown(f'<p style="color: #ef4444; font-size: 11px; text-transform: uppercase;">🔻 {year2} Losing Days</p>', unsafe_allow_html=True)
            if len(top_losing) > 0:
                for _, row in top_losing.iterrows():
                    st.markdown(f"""
                        <div style="color: #e5e7eb; font-size: 13px; padding: 4px 0;">
                            <span style="color: #6b7280;">{row['aligned_date'].strftime('%b %d')}</span>
                            <span style="color: #ef4444; margin-left: 8px;">{row['momentum_3day']:.2f}%/day</span>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        st.caption("Not enough data after June 15.")


# =============================================================================
# MAIN
# =============================================================================

def main():
    # Get last updated date from item sales
    last_updated = ""
    try:
        if db_exists():
            result = read_sql("SELECT MAX(date) as max_date FROM sales_featured")
            if len(result) > 0 and result['max_date'].iloc[0]:
                max_date = pd.to_datetime(result['max_date'].iloc[0])
                last_updated = max_date.strftime('%B %d, %Y')
    except:
        pass

    # Check admin mode for attendance adjustment percentage setting
    admin_mode = is_admin_mode()

    # Load the stored adjustment percentage (set by admin)
    if 'attendance_adj_pct' not in st.session_state:
        st.session_state.attendance_adj_pct = load_attendance_adjustment_pct()

    # Check if adjustment is configured (non-zero value set by admin)
    adj_pct_configured = st.session_state.attendance_adj_pct != 0

    # Header layout
    header_col1, header_col2 = st.columns([4, 1])

    # Render controls column FIRST to get toggle state
    with header_col2:
        st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

        # Show styled toggle widget if adjustment is configured (visible to all users)
        if adj_pct_configured:
            # Styled widget container for the toggle
            enabled = st.toggle(
                "Attendance Adjusted",
                value=st.session_state.get('attendance_adj_enabled', False),
                key="att_adj_toggle_global",
                help="Adjust prior year data to account for attendance differences"
            )
            st.session_state.attendance_adj_enabled = enabled

            # Admin config button (inline, small)
            if admin_mode:
                with st.popover("Config", use_container_width=True):
                    st.markdown("**Set Adjustment % (Admin Only)**")
                    adj_pct = st.slider(
                        "Attendance Change %",
                        min_value=-50,
                        max_value=50,
                        value=int(st.session_state.get('attendance_adj_pct', 0)),
                        step=1,
                        help="Negative = attendance down",
                        key="att_adj_slider"
                    )

                    if adj_pct != st.session_state.attendance_adj_pct:
                        st.session_state.attendance_adj_pct = adj_pct
                        save_attendance_adjustment_pct(adj_pct)
                        st.success("Saved!")

                    if adj_pct != 0:
                        direction = "down" if adj_pct < 0 else "up"
                        factor = 1 + (adj_pct / 100)
                        st.caption(f"Attendance {direction} {abs(adj_pct)}% → prior year x{factor:.2f}")
        else:
            enabled = False
            # Admin setup button when not configured
            if admin_mode:
                with st.popover("Setup Attendance Adj.", use_container_width=True):
                    st.markdown("**Attendance Adjustment Setup**")
                    st.caption("Normalize comparisons for attendance differences")

                    adj_pct = st.slider(
                        "Attendance Change %",
                        min_value=-50,
                        max_value=50,
                        value=0,
                        step=1,
                        help="Negative = attendance down (e.g., -10 for 10% down)",
                        key="att_adj_slider_setup"
                    )

                    if st.button("Save & Enable Toggle", type="primary", use_container_width=True):
                        st.session_state.attendance_adj_pct = adj_pct
                        save_attendance_adjustment_pct(adj_pct)
                        st.success("Saved! Refresh to see toggle.")
                        st.rerun()

        # Upload button below the toggle
        with st.popover("Upload Data", use_container_width=True):
            render_upload_compact()

    # Now render header with badge based on current toggle state
    with header_col1:
        last_updated_text = f" · Updated {last_updated}" if last_updated else ""

        # Show attendance adjustment indicator if toggle is ON
        adj_active = enabled and st.session_state.get('attendance_adj_pct', 0) != 0
        norm_indicator = '<span style="background: rgba(234, 179, 8, 0.2); color: #eab308; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 12px;">ATTENDANCE ADJUSTED</span>' if adj_active else ''

        st.markdown(f"""
            <div class="dash-header">
                <div>
                    <span class="dash-title">Canobie Lake Park</span>{norm_indicator}
                </div>
                <div class="dash-subtitle">Food & Beverage Sales Dashboard{last_updated_text}</div>
            </div>
        """, unsafe_allow_html=True)

    df = load_sales_data()

    if df is None or len(df) == 0:
        st.warning("No data found. Use the Upload Data button above to get started.")
        return

    # Check for missing uploads in last 2 weeks (admin only)
    if admin_mode:
        try:
            # Get dates with data in current year
            current_year = datetime.now().year
            today = datetime.now().date()
            two_weeks_ago = today - timedelta(days=14)

            # Get all dates that have uploads
            uploaded_dates = set(pd.to_datetime(df[df['year'] == current_year]['date']).dt.date.unique())

            # Generate expected dates (last 2 weeks, excluding today)
            expected_dates = set()
            for i in range(1, 15):  # 1 to 14 days ago
                expected_dates.add(today - timedelta(days=i))

            # Find missing dates
            missing_dates = sorted(expected_dates - uploaded_dates)

            if missing_dates:
                missing_str = ", ".join([d.strftime('%b %d') for d in missing_dates])
                st.warning(f"⚠️ **Missing uploads** (last 2 weeks): {missing_str}")
        except:
            pass  # Silently fail if check doesn't work

    # Season Race tab only visible in admin mode
    if admin_mode:
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Summary", "Locations", "Items", "Comparison", "Forecast", "Season Race"])
    else:
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["Summary", "Locations", "Items", "Comparison", "Forecast"])

    with tab1:
        render_sales_overview(df)

    with tab2:
        render_locations()

    with tab3:
        render_items(df)

    with tab4:
        render_comparison(df)

    with tab5:
        # Toggle between forecast modes
        forecast_mode = st.radio(
            "Forecast Mode",
            ["Order Planning", "Remaining Season"],
            horizontal=True,
            key="forecast_mode_toggle",
            label_visibility="collapsed"
        )
        st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)
        if forecast_mode == "Order Planning":
            render_forecast(df)
        else:
            render_remaining_season_forecast(df)

    if admin_mode:
        with tab6:
            render_season_race(df)


if __name__ == "__main__":
    main()
