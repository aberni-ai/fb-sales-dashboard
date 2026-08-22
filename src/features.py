"""
Feature engineering module for F&B Item Sales Forecasting Tool.
Adds derived columns to the sales data for analysis and modeling.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz

ET = pytz.timezone('America/New_York')


def load_sales_data(db_path: str) -> pd.DataFrame:
    """Load sales data from SQLite database."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()

    # Convert date string back to datetime
    df['date'] = pd.to_datetime(df['date'], utc=True)
    df['date'] = df['date'].dt.tz_convert(ET)

    return df


def get_season_start(year: int) -> datetime:
    """Get the approximate season start date (May 1st) for a given year."""
    return ET.localize(datetime(year, 5, 1, 12, 0, 0))


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add derived feature columns to the sales dataframe.
    """
    df = df.copy()

    # Basic date features
    df['day_of_week'] = df['date'].dt.day_name()
    df['day_of_week_num'] = df['date'].dt.dayofweek  # 0=Monday, 6=Sunday
    df['month'] = df['date'].dt.month
    df['month_name'] = df['date'].dt.month_name()
    df['year'] = df['date'].dt.year
    df['day_of_month'] = df['date'].dt.day

    # Weekend flag
    df['is_weekend'] = df['day_of_week_num'].isin([5, 6]).astype(int)

    # Week of season (weeks since May 1st of that year)
    def calc_week_of_season(row):
        season_start = get_season_start(row['year'])
        delta = row['date'] - season_start
        return max(1, (delta.days // 7) + 1)

    df['week_of_season'] = df.apply(calc_week_of_season, axis=1)

    # Per-capita metrics
    df['revenue_per_capita'] = df['total_price'] / df['attendance'].replace(0, float('nan'))
    df['qty_per_capita'] = df['total_qty'] / df['attendance'].replace(0, float('nan'))

    # Fill NaN values for per-capita metrics
    df['revenue_per_capita'] = df['revenue_per_capita'].fillna(0)
    df['qty_per_capita'] = df['qty_per_capita'].fillna(0)

    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add rolling average features. Must be done after basic features.
    Computes rolling 7-day averages per item.
    """
    df = df.copy()
    df = df.sort_values(['plu', 'date'])

    # Rolling 7-day average quantity per item
    df['rolling_7day_avg_qty'] = df.groupby('plu')['total_qty'].transform(
        lambda x: x.rolling(7, min_periods=1).mean()
    )

    # Rolling 7-day average attendance (same for all items on a given date)
    date_attendance = df[['date', 'attendance']].drop_duplicates().sort_values('date')
    date_attendance['rolling_7day_avg_attendance'] = date_attendance['attendance'].rolling(
        7, min_periods=1
    ).mean()

    df = df.merge(
        date_attendance[['date', 'rolling_7day_avg_attendance']],
        on='date',
        how='left'
    )

    return df


def engineer_features(db_path: str, output_db_path: str = None) -> pd.DataFrame:
    """
    Main function to load data and add all features.
    Optionally saves to a new database table.
    """
    if output_db_path is None:
        output_db_path = db_path

    print("Loading sales data...")
    df = load_sales_data(db_path)
    print(f"Loaded {len(df)} records")

    print("Adding basic features...")
    df = add_features(df)

    print("Adding rolling features...")
    df = add_rolling_features(df)

    print(f"Final dataset: {len(df)} records with {len(df.columns)} columns")

    # Save to database
    print("Saving featured data to database...")
    conn = sqlite3.connect(output_db_path)

    # Convert datetime to string for SQLite
    df['date'] = df['date'].dt.strftime('%Y-%m-%d %H:%M:%S')

    df.to_sql('sales_featured', conn, index=False, if_exists='replace')

    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_featured_date ON sales_featured(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_featured_plu ON sales_featured(plu)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_featured_year ON sales_featured(year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_featured_month ON sales_featured(month)")

    conn.commit()
    conn.close()

    print("Feature engineering complete!")
    return df


def main():
    """Run feature engineering from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='Add features to F&B sales data')
    parser.add_argument('--db', default='fb_sales.db', help='SQLite database path')

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    db_path = project_root / args.db

    engineer_features(str(db_path))


if __name__ == '__main__':
    main()
