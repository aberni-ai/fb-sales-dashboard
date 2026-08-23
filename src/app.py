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
        font-size: 14px !important;
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
        date_range = st.selectbox("Date Range", ["Year to Date", "Full Season", "Custom Range"], key="comp_daterange")

    with col4:
        metric = st.selectbox("Metric", ["Sales ($)", "Units Sold"], key="comp_metric")

    # Row 2: Year selection and custom dates
    col1, col2, col3, col4 = st.columns([1.5, 1.5, 1, 1])

    with col1:
        selected_years = st.multiselect("Years to Compare", [str(y) for y in years], default=[str(y) for y in years], key="comp_years")

    if date_range == "Custom Range":
        with col2:
            start_date = st.date_input("Start", value=df['date'].min().date(), key="comp_start")
        with col3:
            end_date = st.date_input("End", value=df['date'].max().date(), key="comp_end")

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
    elif date_range == "Custom Range":
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

    # Build column config for proper formatting
    col_config = {compare_by: st.column_config.TextColumn(compare_by)}
    for col in year_cols:
        if metric == "Sales ($)":
            col_config[col] = st.column_config.NumberColumn(col, format="$%,.0f")
        else:
            col_config[col] = st.column_config.NumberColumn(col, format="%,.0f")

    if 'Change' in pivot_display.columns:
        if metric == "Sales ($)":
            col_config['Change'] = st.column_config.NumberColumn('Change', format="$%,.0f")
        else:
            col_config['Change'] = st.column_config.NumberColumn('Change', format="%,.0f")
        col_config['Change %'] = st.column_config.NumberColumn('Change %', format="%.1f%%")

    st.dataframe(pivot_display, column_config=col_config, use_container_width=True, hide_index=True, height=250)
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

        # Build column config for YTD comparison (with commas)
        col_config = {}
        for col in display_data.columns:
            if col.startswith('Sales'):
                col_config[col] = st.column_config.NumberColumn(col, format="$%,.0f")
            elif col.startswith('Qty'):
                col_config[col] = st.column_config.NumberColumn(col, format="%,.0f")
            elif col == 'Change':
                col_config[col] = st.column_config.NumberColumn('Change', format="$%,.0f")
            elif col == 'Change %':
                col_config[col] = st.column_config.NumberColumn('Change %', format="%.1f%%")
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

    # Build column config for proper sorting with formatted display (with commas)
    col_config = {}
    for col in location_summary.columns:
        if col == 'Location':
            continue
        elif col == 'Days':
            col_config[col] = st.column_config.NumberColumn(col, format="%,d")
        elif 'Change %' in col:
            col_config[col] = st.column_config.NumberColumn(col, format="%.1f%%")
        elif 'Change' in col or 'Sales' in col or 'Avg' in col:
            col_config[col] = st.column_config.NumberColumn(col, format="$%,.0f")

    st.dataframe(location_summary, column_config=col_config, use_container_width=True, hide_index=True, height=400)
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
        st.session_state.attendance_adj_enabled = False

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

    # Header layout: always show attendance toggle if configured, admin gets more controls
    header_col1, header_col2, header_col3 = st.columns([3.2, 1.3, 1])

    with header_col1:
        last_updated_text = f" · Updated {last_updated}" if last_updated else ""

        # Show attendance adjustment indicator if enabled
        adj_active = st.session_state.get('attendance_adj_enabled', False) and st.session_state.get('attendance_adj_pct', 0) != 0
        norm_indicator = '<span style="background: rgba(234, 179, 8, 0.2); color: #eab308; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-left: 12px;">ATT. ADJUSTED</span>' if adj_active else ''

        st.markdown(f"""
            <div class="dash-header">
                <div>
                    <span class="dash-title">Canobie Lake Park</span>
                    <span class="badge">F&B Sales</span>{norm_indicator}
                </div>
                <div class="dash-subtitle">Food & Beverage Sales Dashboard{last_updated_text}</div>
            </div>
        """, unsafe_allow_html=True)

    # Attendance adjustment control - toggle visible directly in header
    with header_col2:
        st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

        # Show toggle directly in header if adjustment is configured (visible to all users)
        if adj_pct_configured:
            # Toggle visible directly in header for all users
            enabled = st.toggle(
                "Att. Adjusted",
                value=st.session_state.get('attendance_adj_enabled', False),
                key="att_adj_toggle_global",
                help="Adjust prior year data to account for attendance differences"
            )
            st.session_state.attendance_adj_enabled = enabled

            # Admin-only: small button to configure the percentage
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
                        st.caption(f"Att. {direction} {abs(adj_pct)}% → prior year x{factor:.2f}")

        elif admin_mode:
            # Admin but no adjustment configured yet - show setup button
            with st.popover("Att. Setup", use_container_width=True):
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


    with header_col3:
        st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
        with st.popover("Upload", use_container_width=True):
            render_upload_compact()

    df = load_sales_data()

    if df is None or len(df) == 0:
        st.warning("No data found. Use the Upload Data button above to get started.")
        return

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


if __name__ == "__main__":
    main()
