"""
Database abstraction layer for F&B Sales Dashboard.
Supports both SQLite (local development) and PostgreSQL (Supabase cloud).
"""

import os
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

# Check if we're running in cloud mode (Supabase)
def is_cloud_mode():
    """Check if Supabase credentials are configured."""
    try:
        return 'supabase' in st.secrets and 'url' in st.secrets['supabase']
    except:
        return False


def get_supabase_connection():
    """Get PostgreSQL connection string for Supabase."""
    secrets = st.secrets['supabase']
    # Supabase connection string format
    return f"postgresql://{secrets['user']}:{secrets['password']}@{secrets['host']}:{secrets['port']}/{secrets['database']}"


def get_connection():
    """Get database connection - PostgreSQL for cloud, SQLite for local."""
    if is_cloud_mode():
        from sqlalchemy import create_engine
        engine = create_engine(get_supabase_connection())
        return engine.connect()
    else:
        # Local SQLite
        project_root = Path(__file__).parent.parent
        db_path = project_root / 'fb_sales.db'
        return sqlite3.connect(str(db_path))


def read_sql(query, params=None):
    """Execute a read query and return DataFrame."""
    if is_cloud_mode():
        from sqlalchemy import create_engine, text
        engine = create_engine(get_supabase_connection())
        with engine.connect() as conn:
            if params:
                return pd.read_sql(text(query), conn, params=params)
            return pd.read_sql(text(query), conn)
    else:
        project_root = Path(__file__).parent.parent
        db_path = project_root / 'fb_sales.db'
        conn = sqlite3.connect(str(db_path))
        result = pd.read_sql_query(query, conn, params=params)
        conn.close()
        return result


def execute_sql(query, params=None):
    """Execute a write query."""
    if is_cloud_mode():
        from sqlalchemy import create_engine, text
        engine = create_engine(get_supabase_connection())
        with engine.connect() as conn:
            if params:
                conn.execute(text(query), params)
            else:
                conn.execute(text(query))
            conn.commit()
    else:
        project_root = Path(__file__).parent.parent
        db_path = project_root / 'fb_sales.db'
        conn = sqlite3.connect(str(db_path))
        if params:
            conn.execute(query, params)
        else:
            conn.execute(query)
        conn.commit()
        conn.close()


def save_dataframe(df, table_name, if_exists='append'):
    """Save a DataFrame to the database."""
    if is_cloud_mode():
        from sqlalchemy import create_engine
        engine = create_engine(get_supabase_connection())
        df.to_sql(table_name, engine, index=False, if_exists=if_exists)
    else:
        project_root = Path(__file__).parent.parent
        db_path = project_root / 'fb_sales.db'
        conn = sqlite3.connect(str(db_path))
        df.to_sql(table_name, conn, index=False, if_exists=if_exists)
        conn.close()


def delete_by_dates(table_name, dates):
    """Delete records for specific dates (for upsert logic)."""
    if not dates:
        return

    if is_cloud_mode():
        from sqlalchemy import create_engine, text
        engine = create_engine(get_supabase_connection())
        with engine.connect() as conn:
            for date in dates:
                conn.execute(text(f"DELETE FROM {table_name} WHERE date = :date"), {"date": date})
            conn.commit()
    else:
        project_root = Path(__file__).parent.parent
        db_path = project_root / 'fb_sales.db'
        conn = sqlite3.connect(str(db_path))
        for date in dates:
            conn.execute(f"DELETE FROM {table_name} WHERE date = ?", (date,))
        conn.commit()
        conn.close()


def table_exists(table_name):
    """Check if a table exists in the database."""
    if is_cloud_mode():
        from sqlalchemy import create_engine, text
        engine = create_engine(get_supabase_connection())
        with engine.connect() as conn:
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :name)"
            ), {"name": table_name})
            return result.scalar()
    else:
        project_root = Path(__file__).parent.parent
        db_path = project_root / 'fb_sales.db'
        if not db_path.exists():
            return False
        conn = sqlite3.connect(str(db_path))
        result = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            conn, params=(table_name,)
        )
        conn.close()
        return len(result) > 0


def db_exists():
    """Check if the database exists and has data."""
    if is_cloud_mode():
        return table_exists('sales_featured')
    else:
        project_root = Path(__file__).parent.parent
        db_path = project_root / 'fb_sales.db'
        return db_path.exists()


def get_db_info():
    """Get info about current database mode."""
    if is_cloud_mode():
        return "Cloud (Supabase PostgreSQL)"
    else:
        return "Local (SQLite)"
