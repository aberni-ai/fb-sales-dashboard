"""
Data ingestion module for F&B Item Sales Forecasting Tool.
Parses 610 daily sales Excel files and attendance data, consolidates into SQLite.
"""

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytz

# Eastern timezone
ET = pytz.timezone('America/New_York')


def parse_date_from_row2(df: pd.DataFrame) -> datetime | None:
    """
    Extract the operating date from Row 2 of the sales file.
    Format: 'FromDate Saturday, October 25, 2025\nEndDate Saturday, October 25, 2025'
    or similar variations.
    """
    try:
        # Row 2 is index 1 (0-indexed), first column
        cell_value = str(df.iloc[1, 0])

        # Try to find a date pattern like "October 25, 2025"
        # Match: Month Day, Year
        pattern = r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})'
        match = re.search(pattern, cell_value)

        if match:
            month_str, day_str, year_str = match.groups()
            date_str = f"{month_str} {day_str}, {year_str}"
            dt = datetime.strptime(date_str, "%B %d, %Y")
            # Store as noon Eastern Time
            return ET.localize(dt.replace(hour=12))

        return None
    except Exception:
        return None


def load_attendance(attendance_path: str) -> pd.DataFrame:
    """
    Load attendance data from all available year sheets (2023-2026+).
    Returns DataFrame with Date and Attendance columns.
    """
    all_attendance = []

    xlsx = pd.ExcelFile(attendance_path)
    for sheet_name in ['2023', '2024', '2025', '2026']:
        if sheet_name in xlsx.sheet_names:
            df = pd.read_excel(xlsx, sheet_name=sheet_name)
            # Normalize column names
            df.columns = [str(c).strip().lower() for c in df.columns]

            # Find date and attendance columns
            date_col = None
            att_col = None
            for col in df.columns:
                if 'date' in col:
                    date_col = col
                if 'attendance' in col:
                    att_col = col

            if date_col and att_col:
                temp = df[[date_col, att_col]].copy()
                temp.columns = ['date', 'attendance']
                temp['date'] = pd.to_datetime(temp['date'], errors='coerce')
                temp = temp.dropna(subset=['date'])
                temp['attendance'] = pd.to_numeric(temp['attendance'], errors='coerce').fillna(0)
                all_attendance.append(temp)

    if all_attendance:
        result = pd.concat(all_attendance, ignore_index=True)
        result = result.drop_duplicates(subset=['date'])
        return result

    return pd.DataFrame(columns=['date', 'attendance'])


def parse_sales_file(filepath: str) -> tuple[datetime | None, pd.DataFrame]:
    """
    Parse a single sales Excel file.
    Returns (date, dataframe) or (None, empty_df) if parsing fails.
    """
    try:
        # Read raw to get the date from row 2
        df_raw = pd.read_excel(filepath, header=None, nrows=10)
        operating_date = parse_date_from_row2(df_raw)

        if not operating_date:
            return None, pd.DataFrame()

        # Read the actual data starting from row 7 (0-indexed: 6)
        df = pd.read_excel(filepath, header=6)

        # Normalize column names
        df.columns = [str(c).strip() for c in df.columns]

        # Map to expected column names
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

        # Keep only expected columns
        expected_cols = ['plu', 'plu_name', 'sold_qty', 'returned_qty',
                         'total_qty', 'average_price', 'total_price']
        available_cols = [c for c in expected_cols if c in df.columns]
        df = df[available_cols]

        # Skip the "Total" row (last row) - check if PLU is 'Total' or empty with large values
        if len(df) > 0:
            # Remove rows where PLU contains 'Total' (case insensitive)
            df = df[~df['plu'].astype(str).str.lower().str.contains('total', na=False)]

        # Convert numeric columns
        for col in ['sold_qty', 'returned_qty', 'total_qty', 'average_price', 'total_price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Add date column
        df['date'] = operating_date

        return operating_date, df

    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None, pd.DataFrame()


def ingest_all(sales_folder: str, attendance_path: str, db_path: str) -> dict:
    """
    Main ingestion function. Reads all sales files and attendance,
    consolidates into SQLite database.
    Sales are ingested independently of attendance - attendance is joined when available.
    Returns stats dict with counts.
    """
    stats = {
        'total_files': 0,
        'ingested_files': 0,
        'skipped_files': 0,
        'skipped_reasons': {
            'no_date_parsed': 0
        },
        'total_records': 0,
        'with_attendance': 0,
        'without_attendance': 0
    }

    # Load attendance data (optional - sales don't depend on it)
    print("Loading attendance data...")
    attendance_df = load_attendance(attendance_path)
    print(f"Loaded {len(attendance_df)} attendance records")

    # Build attendance lookup (all dates, not just > 0)
    attendance_lookup = {}
    for _, row in attendance_df.iterrows():
        date_key = row['date'].date() if hasattr(row['date'], 'date') else row['date']
        attendance_lookup[date_key] = row['attendance']

    print(f"Found {len(attendance_lookup)} attendance records for lookup")

    # Get all sales files
    sales_folder = Path(sales_folder)
    sales_files = list(sales_folder.glob("*.xlsx"))
    stats['total_files'] = len(sales_files)
    print(f"Found {len(sales_files)} sales files")

    all_sales = []

    for i, filepath in enumerate(sales_files):
        if (i + 1) % 50 == 0:
            print(f"Processing file {i + 1}/{len(sales_files)}...")

        operating_date, df = parse_sales_file(str(filepath))

        if operating_date is None:
            stats['skipped_files'] += 1
            stats['skipped_reasons']['no_date_parsed'] += 1
            continue

        date_key = operating_date.date()

        # Add attendance if available, otherwise NULL
        if date_key in attendance_lookup:
            df['attendance'] = attendance_lookup[date_key]
            stats['with_attendance'] += 1
        else:
            df['attendance'] = None
            stats['without_attendance'] += 1

        all_sales.append(df)
        stats['ingested_files'] += 1

    # Consolidate all sales data
    if all_sales:
        print("Consolidating data...")
        consolidated = pd.concat(all_sales, ignore_index=True)

        # Remove duplicate date/PLU combinations (from duplicate files)
        before_dedup = len(consolidated)
        consolidated = consolidated.drop_duplicates(subset=['date', 'plu'], keep='first')
        after_dedup = len(consolidated)
        if before_dedup > after_dedup:
            print(f"Removed {before_dedup - after_dedup} duplicate date/PLU records")

        stats['total_records'] = len(consolidated)

        # Convert date to string for SQLite storage (ISO format)
        consolidated['date_str'] = consolidated['date'].dt.strftime('%Y-%m-%d %H:%M:%S%z')

        # Save to SQLite
        print(f"Saving {len(consolidated)} records to SQLite...")
        conn = sqlite3.connect(db_path)

        # Drop existing table if exists
        conn.execute("DROP TABLE IF EXISTS sales")
        conn.execute("DROP TABLE IF EXISTS attendance")

        # Save sales data
        consolidated.drop(columns=['date'], inplace=True)
        consolidated.rename(columns={'date_str': 'date'}, inplace=True)
        consolidated.to_sql('sales', conn, index=False, if_exists='replace')

        # Save attendance data
        attendance_df['date'] = attendance_df['date'].dt.strftime('%Y-%m-%d')
        attendance_df.to_sql('attendance', conn, index=False, if_exists='replace')

        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_plu ON sales(plu)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)")

        conn.commit()
        conn.close()
        print("Database saved successfully!")

    return stats


def main():
    """Run ingestion from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='Ingest F&B sales data')
    parser.add_argument('--sales', default='data/sales', help='Path to sales folder')
    parser.add_argument('--attendance', default='data/attendance.xlsx', help='Path to attendance file')
    parser.add_argument('--db', default='fb_sales.db', help='Output SQLite database path')

    args = parser.parse_args()

    # Get the project root (parent of src)
    project_root = Path(__file__).parent.parent

    sales_path = project_root / args.sales
    attendance_path = project_root / args.attendance
    db_path = project_root / args.db

    print(f"Sales folder: {sales_path}")
    print(f"Attendance file: {attendance_path}")
    print(f"Database: {db_path}")

    stats = ingest_all(str(sales_path), str(attendance_path), str(db_path))

    print("\n=== Ingestion Summary ===")
    print(f"Total files found: {stats['total_files']}")
    print(f"Files ingested: {stats['ingested_files']}")
    print(f"Files skipped: {stats['skipped_files']}")
    print(f"  - No date parsed: {stats['skipped_reasons']['no_date_parsed']}")
    print(f"Days with attendance data: {stats['with_attendance']}")
    print(f"Days without attendance data: {stats['without_attendance']}")
    print(f"Total records saved: {stats['total_records']}")


if __name__ == '__main__':
    main()
