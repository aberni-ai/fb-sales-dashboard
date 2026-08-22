"""
Analysis and insights module for F&B Item Sales Forecasting Tool.
Provides reports and analytics on sales patterns.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import numpy as np


def load_featured_data(db_path: str) -> pd.DataFrame:
    """Load featured sales data from SQLite database."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM sales_featured", conn)
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    return df


def top_sellers(df: pd.DataFrame, by: str = 'total_qty', top_n: int = 20,
                year: int = None, month: int = None, day_of_week: str = None) -> pd.DataFrame:
    """
    Get top selling items by quantity or revenue.

    Args:
        df: Sales dataframe
        by: 'total_qty' or 'total_price'
        top_n: Number of items to return
        year: Filter by year (optional)
        month: Filter by month (optional)
        day_of_week: Filter by day of week (optional)
    """
    filtered = df.copy()

    if year:
        filtered = filtered[filtered['year'] == year]
    if month:
        filtered = filtered[filtered['month'] == month]
    if day_of_week:
        filtered = filtered[filtered['day_of_week'] == day_of_week]

    agg = filtered.groupby(['plu', 'plu_name']).agg({
        'total_qty': 'sum',
        'total_price': 'sum',
        'date': 'nunique'
    }).reset_index()

    agg.columns = ['plu', 'plu_name', 'total_qty', 'total_revenue', 'days_sold']
    agg = agg.sort_values(by, ascending=False).head(top_n)

    return agg


def per_capita_analysis(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Analyze items by per-capita performance.
    Returns items ranked by average qty per capita.
    """
    agg = df.groupby(['plu', 'plu_name']).agg({
        'qty_per_capita': 'mean',
        'revenue_per_capita': 'mean',
        'total_qty': 'sum',
        'total_price': 'sum',
        'date': 'nunique'
    }).reset_index()

    agg.columns = ['plu', 'plu_name', 'avg_qty_per_capita', 'avg_revenue_per_capita',
                   'total_qty', 'total_revenue', 'days_sold']

    # Best performers
    best = agg.sort_values('avg_qty_per_capita', ascending=False).head(top_n)
    best['rank_type'] = 'top_performer'

    # Worst performers (with minimum days threshold)
    min_days = agg['days_sold'].quantile(0.25)
    worst = agg[agg['days_sold'] >= min_days].sort_values(
        'avg_qty_per_capita', ascending=True
    ).head(top_n)
    worst['rank_type'] = 'underperformer'

    return pd.concat([best, worst])


def yoy_trends(df: pd.DataFrame, min_days: int = 10) -> pd.DataFrame:
    """
    Year-over-year trend analysis.
    Shows items growing or declining compared to previous year.
    """
    years = sorted(df['year'].unique())
    if len(years) < 2:
        return pd.DataFrame()

    # Calculate yearly totals per item
    yearly = df.groupby(['plu', 'plu_name', 'year']).agg({
        'total_qty': 'sum',
        'total_price': 'sum',
        'date': 'nunique'
    }).reset_index()

    yearly.columns = ['plu', 'plu_name', 'year', 'total_qty', 'total_revenue', 'days_sold']

    # Pivot to compare years
    pivot = yearly.pivot_table(
        index=['plu', 'plu_name'],
        columns='year',
        values=['total_qty', 'total_revenue', 'days_sold'],
        fill_value=0
    )

    pivot.columns = ['_'.join(map(str, col)) for col in pivot.columns]
    pivot = pivot.reset_index()

    # Calculate YoY change for the last two years
    last_year = years[-1]
    prev_year = years[-2]

    qty_last = f'total_qty_{last_year}'
    qty_prev = f'total_qty_{prev_year}'
    days_last = f'days_sold_{last_year}'
    days_prev = f'days_sold_{prev_year}'

    if qty_last in pivot.columns and qty_prev in pivot.columns:
        pivot['qty_yoy_change'] = pivot[qty_last] - pivot[qty_prev]
        pivot['qty_yoy_pct'] = (pivot[qty_last] / pivot[qty_prev].replace(0, np.nan) - 1) * 100

        # Filter to items with sufficient data
        pivot = pivot[(pivot[days_last] >= min_days) | (pivot[days_prev] >= min_days)]

        # Top growers and decliners
        growers = pivot.nlargest(20, 'qty_yoy_pct')[
            ['plu', 'plu_name', qty_prev, qty_last, 'qty_yoy_change', 'qty_yoy_pct']
        ]
        growers['trend'] = 'growing'

        decliners = pivot.nsmallest(20, 'qty_yoy_pct')[
            ['plu', 'plu_name', qty_prev, qty_last, 'qty_yoy_change', 'qty_yoy_pct']
        ]
        decliners['trend'] = 'declining'

        return pd.concat([growers, decliners])

    return pd.DataFrame()


def day_of_week_patterns(df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """
    Analyze day-of-week patterns for items.
    Identifies items that spike on weekends vs weekdays.
    """
    # Calculate average daily qty by item and weekend flag
    dow_avg = df.groupby(['plu', 'plu_name', 'is_weekend']).agg({
        'total_qty': 'mean'
    }).reset_index()

    dow_pivot = dow_avg.pivot_table(
        index=['plu', 'plu_name'],
        columns='is_weekend',
        values='total_qty',
        fill_value=0
    ).reset_index()

    dow_pivot.columns = ['plu', 'plu_name', 'weekday_avg', 'weekend_avg']

    dow_pivot['weekend_lift'] = (
        (dow_pivot['weekend_avg'] / dow_pivot['weekday_avg'].replace(0, np.nan) - 1) * 100
    )

    # Top weekend items
    weekend_items = dow_pivot.nlargest(top_n, 'weekend_lift')[
        ['plu', 'plu_name', 'weekday_avg', 'weekend_avg', 'weekend_lift']
    ]
    weekend_items['pattern'] = 'weekend_spike'

    # Top weekday items
    weekday_items = dow_pivot.nsmallest(top_n, 'weekend_lift')[
        ['plu', 'plu_name', 'weekday_avg', 'weekend_avg', 'weekend_lift']
    ]
    weekday_items['pattern'] = 'weekday_preferred'

    return pd.concat([weekend_items, weekday_items])


def seasonality_curves(df: pd.DataFrame, plu: str = None) -> pd.DataFrame:
    """
    Get seasonality curves (weekly averages across the season).
    If plu is specified, returns curve for that item.
    Otherwise returns aggregated seasonal pattern.
    """
    filtered = df.copy()

    if plu:
        filtered = filtered[filtered['plu'] == plu]

    # Group by week of season
    seasonal = filtered.groupby('week_of_season').agg({
        'total_qty': 'mean',
        'total_price': 'mean',
        'attendance': 'mean',
        'qty_per_capita': 'mean'
    }).reset_index()

    seasonal.columns = ['week_of_season', 'avg_qty', 'avg_revenue',
                        'avg_attendance', 'avg_qty_per_capita']

    return seasonal


def attendance_correlation(df: pd.DataFrame, min_days: int = 20) -> pd.DataFrame:
    """
    Calculate correlation between item sales and attendance.
    Returns items ranked by correlation strength.
    """
    # Get daily totals per item
    daily = df.groupby(['plu', 'plu_name', 'date', 'attendance']).agg({
        'total_qty': 'sum'
    }).reset_index()

    # Calculate correlation per item
    correlations = []
    for (plu, plu_name), group in daily.groupby(['plu', 'plu_name']):
        if len(group) >= min_days:
            corr = group['total_qty'].corr(group['attendance'])
            correlations.append({
                'plu': plu,
                'plu_name': plu_name,
                'attendance_correlation': corr,
                'days_sold': len(group)
            })

    corr_df = pd.DataFrame(correlations)
    corr_df = corr_df.sort_values('attendance_correlation', ascending=False)

    return corr_df


def revenue_concentration(df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze revenue concentration (Pareto analysis).
    What % of revenue comes from top N items?
    """
    # Total revenue per item
    item_revenue = df.groupby(['plu', 'plu_name']).agg({
        'total_price': 'sum'
    }).reset_index()

    item_revenue = item_revenue.sort_values('total_price', ascending=False)
    total_revenue = item_revenue['total_price'].sum()

    item_revenue['revenue_pct'] = (item_revenue['total_price'] / total_revenue) * 100
    item_revenue['cumulative_pct'] = item_revenue['revenue_pct'].cumsum()
    item_revenue['rank'] = range(1, len(item_revenue) + 1)

    # Summary stats
    top_10_pct = item_revenue[item_revenue['rank'] <= 10]['revenue_pct'].sum()
    top_20_pct = item_revenue[item_revenue['rank'] <= 20]['revenue_pct'].sum()
    top_50_pct = item_revenue[item_revenue['rank'] <= 50]['revenue_pct'].sum()

    print(f"Revenue Concentration:")
    print(f"  Top 10 items: {top_10_pct:.1f}% of revenue")
    print(f"  Top 20 items: {top_20_pct:.1f}% of revenue")
    print(f"  Top 50 items: {top_50_pct:.1f}% of revenue")

    return item_revenue


def detect_anomalies(df: pd.DataFrame, std_threshold: float = 2.5) -> pd.DataFrame:
    """
    Detect anomalous sales days for each item.
    Flags days where sales deviate significantly from expected
    (based on day of week and attendance).
    """
    df = df.copy()

    # Calculate expected qty based on attendance and day of week
    # Use a simple linear model: expected = intercept + coef * attendance
    anomalies = []

    for plu, group in df.groupby('plu'):
        if len(group) < 20:
            continue

        # Calculate mean and std for this item
        mean_qty = group['total_qty'].mean()
        std_qty = group['total_qty'].std()

        if std_qty == 0:
            continue

        # Z-score
        group['z_score'] = (group['total_qty'] - mean_qty) / std_qty

        # Flag anomalies
        anomaly_days = group[abs(group['z_score']) > std_threshold]

        for _, row in anomaly_days.iterrows():
            anomalies.append({
                'date': row['date'],
                'plu': row['plu'],
                'plu_name': row['plu_name'],
                'total_qty': row['total_qty'],
                'expected_qty': mean_qty,
                'z_score': row['z_score'],
                'attendance': row['attendance'],
                'day_of_week': row['day_of_week']
            })

    return pd.DataFrame(anomalies)


def generate_summary_report(db_path: str) -> dict:
    """
    Generate a comprehensive summary report.
    """
    df = load_featured_data(db_path)

    report = {
        'data_summary': {
            'total_records': len(df),
            'unique_items': df['plu'].nunique(),
            'unique_dates': df['date'].dt.date.nunique(),
            'date_range': f"{df['date'].min().date()} to {df['date'].max().date()}",
            'years': sorted(df['year'].unique().tolist()),
            'total_revenue': df['total_price'].sum(),
            'total_quantity': df['total_qty'].sum()
        },
        'top_sellers_by_qty': top_sellers(df, by='total_qty', top_n=10),
        'top_sellers_by_revenue': top_sellers(df, by='total_price', top_n=10),
        'per_capita': per_capita_analysis(df, top_n=10),
        'yoy_trends': yoy_trends(df),
        'dow_patterns': day_of_week_patterns(df, top_n=10),
        'attendance_corr': attendance_correlation(df),
        'revenue_concentration': revenue_concentration(df)
    }

    return report


def main():
    """Run analysis from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze F&B sales data')
    parser.add_argument('--db', default='fb_sales.db', help='SQLite database path')
    parser.add_argument('--report', choices=['summary', 'top', 'trends', 'dow', 'anomalies'],
                        default='summary', help='Report type to generate')

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    db_path = project_root / args.db

    df = load_featured_data(str(db_path))
    print(f"Loaded {len(df)} records\n")

    if args.report == 'summary':
        print("=== Data Summary ===")
        print(f"Total records: {len(df)}")
        print(f"Unique items: {df['plu'].nunique()}")
        print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        print(f"Total revenue: ${df['total_price'].sum():,.2f}")
        print(f"Total quantity sold: {df['total_qty'].sum():,.0f}")

    elif args.report == 'top':
        print("=== Top Sellers by Quantity ===")
        print(top_sellers(df, by='total_qty', top_n=20).to_string(index=False))

    elif args.report == 'trends':
        print("=== Year-over-Year Trends ===")
        print(yoy_trends(df).to_string(index=False))

    elif args.report == 'dow':
        print("=== Day of Week Patterns ===")
        print(day_of_week_patterns(df).to_string(index=False))

    elif args.report == 'anomalies':
        print("=== Anomaly Detection ===")
        anomalies = detect_anomalies(df)
        print(f"Found {len(anomalies)} anomalies")
        if len(anomalies) > 0:
            print(anomalies.head(20).to_string(index=False))


if __name__ == '__main__':
    main()
