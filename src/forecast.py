"""
Forecasting module for F&B Item Sales Forecasting Tool.
Predicts item quantities and revenue for future dates given expected attendance.

Model is only trained for items with >= 30 selling days.
Rare items use historical averages instead.
"""

import sqlite3
import pickle
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from sklearn.preprocessing import StandardScaler
import pytz

ET = pytz.timezone('America/New_York')

# Minimum selling days required to use model (otherwise use historical avg)
MIN_SELLING_DAYS = 30


def load_featured_data(db_path: str) -> pd.DataFrame:
    """Load featured sales data from SQLite database."""
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM sales_featured", conn)
    conn.close()
    df['date'] = pd.to_datetime(df['date'])
    return df


def compute_historical_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute historical averages for all items.
    Used for rare items that don't have enough data for model training.
    """
    # Group by PLU and compute averages
    hist_avg = df.groupby('plu').agg({
        'plu_name': 'first',
        'total_qty': 'mean',
        'total_price': 'mean',
        'average_price': 'mean',
        'date': 'nunique'
    }).reset_index()

    hist_avg.columns = ['plu', 'plu_name', 'avg_qty', 'avg_revenue', 'avg_price', 'selling_days']

    # Also compute day-of-week averages
    dow_avg = df.groupby(['plu', 'day_of_week_num']).agg({
        'total_qty': 'mean'
    }).reset_index()
    dow_avg.columns = ['plu', 'day_of_week_num', 'dow_avg_qty']

    return hist_avg, dow_avg


def prepare_training_data(df: pd.DataFrame, min_occurrences: int = MIN_SELLING_DAYS) -> tuple:
    """
    Prepare training data for the forecasting model.
    Only includes items with >= min_occurrences selling days.
    Returns X, y, plu_mapping, and valid_items.
    """
    # Filter to items with sufficient data
    item_counts = df.groupby('plu')['date'].nunique()
    valid_items = item_counts[item_counts >= min_occurrences].index.tolist()

    print(f"Items with >= {min_occurrences} selling days: {len(valid_items)}")
    print(f"Items excluded (rare): {len(item_counts) - len(valid_items)}")

    df = df[df['plu'].isin(valid_items)].copy()

    # Features
    feature_cols = [
        'attendance',
        'day_of_week_num',
        'month',
        'week_of_season',
        'is_weekend'
    ]

    # Create PLU encoding
    df['plu_code'] = pd.Categorical(df['plu']).codes
    plu_mapping = dict(zip(pd.Categorical(df['plu']).codes, df['plu']))

    X = df[feature_cols + ['plu_code']].copy()
    y = df['total_qty'].values

    return X, y, plu_mapping, valid_items


def train_model(db_path: str, model_type: str = 'gbm',
                test_year: int = 2025, min_days: int = MIN_SELLING_DAYS) -> dict:
    """
    Train the forecasting model.

    Args:
        db_path: Path to SQLite database
        model_type: 'ridge' for simple linear, 'gbm' for gradient boosting
        test_year: Year to use for validation (train on all other years)
        min_days: Minimum selling days required to include item in model

    Returns:
        dict with model, scaler, metrics, historical averages, and metadata
    """
    df = load_featured_data(db_path)

    print("=" * 60)
    print("TRAINING FORECAST MODEL")
    print("=" * 60)

    # Compute historical averages for ALL items (used for rare items)
    print("\nComputing historical averages for all items...")
    hist_avg, dow_avg = compute_historical_averages(df)

    # Item statistics
    item_stats = df.groupby('plu').agg({
        'plu_name': 'first',
        'date': 'nunique',
        'total_price': 'sum',
        'total_qty': 'sum'
    }).reset_index()
    item_stats.columns = ['plu', 'plu_name', 'selling_days', 'total_revenue', 'total_qty']

    model_items = item_stats[item_stats['selling_days'] >= min_days]
    rare_items = item_stats[item_stats['selling_days'] < min_days]

    print(f"\nItem breakdown:")
    print(f"  Model items (>= {min_days} days): {len(model_items)} ({model_items['total_revenue'].sum()/item_stats['total_revenue'].sum()*100:.1f}% of revenue)")
    print(f"  Rare items (< {min_days} days): {len(rare_items)} ({rare_items['total_revenue'].sum()/item_stats['total_revenue'].sum()*100:.1f}% of revenue)")

    print(f"\nTraining on years before {test_year}, testing on {test_year}")

    # Split by year
    train_df = df[df['year'] < test_year]
    test_df = df[df['year'] == test_year]

    if len(train_df) == 0 or len(test_df) == 0:
        print("Using random train/test split instead")
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)

    print(f"Training samples: {len(train_df)}, Test samples: {len(test_df)}")

    # Prepare features (only for items with enough data)
    X_train, y_train, plu_mapping, valid_items = prepare_training_data(train_df, min_days)

    # Prepare test data with same PLU encoding
    test_df = test_df[test_df['plu'].isin(valid_items)].copy()

    # Create reverse mapping for encoding
    plu_to_code = {v: k for k, v in plu_mapping.items()}
    test_df['plu_code'] = test_df['plu'].map(plu_to_code)
    test_df = test_df.dropna(subset=['plu_code'])
    test_df['plu_code'] = test_df['plu_code'].astype(int)

    feature_cols = ['attendance', 'day_of_week_num', 'month', 'week_of_season', 'is_weekend', 'plu_code']
    X_test = test_df[feature_cols]
    y_test = test_df['total_qty'].values

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train model
    if model_type == 'gbm':
        model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            random_state=42
        )
    else:
        model = Ridge(alpha=1.0)

    print(f"\nTraining {model_type.upper()} model...")
    model.fit(X_train_scaled, y_train)

    # Evaluate
    y_pred = model.predict(X_test_scaled)
    y_pred = np.maximum(y_pred, 0)  # Ensure non-negative

    # Overall R²
    r2 = r2_score(y_test, y_pred)

    # Per-item metrics
    test_df = test_df.copy()
    test_df['y_pred'] = y_pred
    test_df['y_actual'] = y_test

    item_metrics = []
    for plu, group in test_df.groupby('plu'):
        actual = group['y_actual'].values
        pred = group['y_pred'].values

        if len(actual) >= 5 and (actual > 0).any():
            # MAPE only on non-zero actuals
            mask = actual > 0
            if mask.sum() > 0:
                item_mape = np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])) * 100
            else:
                item_mape = np.nan
            item_r2 = r2_score(actual, pred) if len(actual) > 1 else np.nan

            # Get revenue for weighting
            item_rev = item_stats[item_stats['plu'] == plu]['total_revenue'].values
            item_rev = item_rev[0] if len(item_rev) > 0 else 0

            item_metrics.append({
                'plu': plu,
                'plu_name': group['plu_name'].iloc[0],
                'mape': item_mape,
                'r2': item_r2,
                'n_samples': len(actual),
                'total_revenue': item_rev
            })

    item_metrics_df = pd.DataFrame(item_metrics)
    item_metrics_df = item_metrics_df.dropna(subset=['mape'])

    # Calculate different MAPE metrics
    mean_mape = item_metrics_df['mape'].mean()
    median_mape = item_metrics_df['mape'].median()

    # Weighted MAPE
    total_rev = item_metrics_df['total_revenue'].sum()
    item_metrics_df['weight'] = item_metrics_df['total_revenue'] / total_rev
    weighted_mape = (item_metrics_df['mape'] * item_metrics_df['weight']).sum()

    print("\n" + "=" * 60)
    print("MODEL PERFORMANCE")
    print("=" * 60)
    print(f"\nOverall R²: {r2:.3f}")
    print(f"\nMAPE Metrics ({len(item_metrics_df)} items with >= {min_days} days):")
    print(f"  Mean MAPE:     {mean_mape:.1f}% (inflated by outliers)")
    print(f"  Median MAPE:   {median_mape:.1f}% (more robust)")
    print(f"  Weighted MAPE: {weighted_mape:.1f}% (revenue-weighted, PRIMARY METRIC)")

    # MAPE distribution
    print(f"\nMAPE Distribution:")
    print(f"  < 50%:    {len(item_metrics_df[item_metrics_df['mape'] < 50])} items")
    print(f"  50-100%:  {len(item_metrics_df[(item_metrics_df['mape'] >= 50) & (item_metrics_df['mape'] < 100)])} items")
    print(f"  100-200%: {len(item_metrics_df[(item_metrics_df['mape'] >= 100) & (item_metrics_df['mape'] < 200)])} items")
    print(f"  > 200%:   {len(item_metrics_df[item_metrics_df['mape'] >= 200])} items")

    # Top 10 best and worst
    print("\n" + "=" * 60)
    print("TOP 10 BEST FORECASTED ITEMS (lowest MAPE)")
    print("-" * 60)
    best_10 = item_metrics_df.nsmallest(10, 'mape')[['plu_name', 'mape', 'r2', 'total_revenue']]
    for _, row in best_10.iterrows():
        print(f"  {row['plu_name'][:35]:35} MAPE: {row['mape']:5.1f}%  R²: {row['r2']:.3f}  Rev: ${row['total_revenue']:,.0f}")

    print("\n" + "=" * 60)
    print("TOP 10 WORST FORECASTED ITEMS (highest MAPE)")
    print("-" * 60)
    worst_10 = item_metrics_df.nlargest(10, 'mape')[['plu_name', 'mape', 'r2', 'total_revenue']]
    for _, row in worst_10.iterrows():
        print(f"  {row['plu_name'][:35]:35} MAPE: {row['mape']:5.1f}%  R²: {row['r2']:.3f}  Rev: ${row['total_revenue']:,.0f}")

    # Build model data
    model_data = {
        'model': model,
        'scaler': scaler,
        'plu_mapping': plu_mapping,
        'valid_items': valid_items,  # Items that use the model
        'feature_cols': feature_cols,
        'metrics': {
            'mean_mape': mean_mape,
            'median_mape': median_mape,
            'weighted_mape': weighted_mape,
            'overall_r2': r2,
            'n_model_items': len(valid_items),
            'n_rare_items': len(rare_items)
        },
        'item_metrics': item_metrics_df,
        'historical_averages': hist_avg,
        'dow_averages': dow_avg,
        'model_type': model_type,
        'min_selling_days': min_days,
        'trained_on': datetime.now().isoformat()
    }

    return model_data


def save_model(model_data: dict, path: str):
    """Save trained model to disk."""
    with open(path, 'wb') as f:
        pickle.dump(model_data, f)
    print(f"\nModel saved to {path}")


def load_model(path: str) -> dict:
    """Load trained model from disk."""
    with open(path, 'rb') as f:
        return pickle.load(f)


def predict(model_data: dict, date: datetime, attendance: int,
            top_n: int = None, include_rare: bool = True) -> pd.DataFrame:
    """
    Predict item quantities for a given date and attendance.

    For items with >= MIN_SELLING_DAYS: uses trained model
    For rare items: uses historical averages (day-of-week adjusted)

    Args:
        model_data: Trained model dict from train_model()
        date: Date to predict for
        attendance: Expected attendance
        top_n: If set, only return top N items by predicted quantity
        include_rare: Whether to include rare items (using historical avg)

    Returns:
        DataFrame with PLU, predicted quantity, and prediction method
    """
    model = model_data['model']
    scaler = model_data['scaler']
    plu_mapping = model_data['plu_mapping']
    hist_avg = model_data['historical_averages']
    dow_avg = model_data['dow_averages']
    valid_items = model_data['valid_items']

    # Calculate features for the date
    day_of_week_num = date.weekday()
    month = date.month
    is_weekend = 1 if day_of_week_num >= 5 else 0
    season_start = datetime(date.year, 5, 1)
    week_of_season = max(1, (date - season_start).days // 7 + 1)

    predictions = []

    # Predict for model items
    for plu_code, plu in plu_mapping.items():
        features = np.array([[
            attendance,
            day_of_week_num,
            month,
            week_of_season,
            is_weekend,
            plu_code
        ]])

        features_scaled = scaler.transform(features)
        pred_qty = max(0, model.predict(features_scaled)[0])

        predictions.append({
            'plu': plu,
            'predicted_qty': round(pred_qty, 1),
            'method': 'model'
        })

    # Predict for rare items using historical averages
    if include_rare:
        rare_items = hist_avg[~hist_avg['plu'].isin(valid_items)]

        for _, row in rare_items.iterrows():
            plu = row['plu']

            # Try to get day-of-week specific average
            dow_row = dow_avg[(dow_avg['plu'] == plu) & (dow_avg['day_of_week_num'] == day_of_week_num)]

            if len(dow_row) > 0:
                pred_qty = dow_row['dow_avg_qty'].values[0]
            else:
                pred_qty = row['avg_qty']

            predictions.append({
                'plu': plu,
                'predicted_qty': round(max(0, pred_qty), 1),
                'method': 'historical_avg'
            })

    pred_df = pd.DataFrame(predictions)
    pred_df = pred_df.sort_values('predicted_qty', ascending=False)

    if top_n:
        pred_df = pred_df.head(top_n)

    return pred_df


def main():
    """Run forecasting from command line."""
    import argparse

    parser = argparse.ArgumentParser(description='F&B Sales Forecasting')
    parser.add_argument('--db', default='fb_sales.db', help='SQLite database path')
    parser.add_argument('--action', choices=['train', 'predict'], default='train')
    parser.add_argument('--model-type', choices=['ridge', 'gbm'], default='gbm')
    parser.add_argument('--model-path', default='forecast_model.pkl')
    parser.add_argument('--min-days', type=int, default=MIN_SELLING_DAYS,
                        help='Minimum selling days for model training')
    parser.add_argument('--date', help='Prediction date (YYYY-MM-DD)')
    parser.add_argument('--attendance', type=int, help='Expected attendance')
    parser.add_argument('--top-n', type=int, default=20, help='Top N items to show')

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    db_path = project_root / args.db
    model_path = project_root / args.model_path

    if args.action == 'train':
        model_data = train_model(str(db_path), model_type=args.model_type,
                                  min_days=args.min_days)
        save_model(model_data, str(model_path))

    elif args.action == 'predict':
        if not args.date or not args.attendance:
            print("Error: --date and --attendance required for prediction")
            return

        model_data = load_model(str(model_path))
        pred_date = datetime.strptime(args.date, '%Y-%m-%d')

        predictions = predict(model_data, pred_date, args.attendance, top_n=args.top_n)

        # Add item names
        hist_avg = model_data['historical_averages']
        name_lookup = dict(zip(hist_avg['plu'], hist_avg['plu_name']))
        predictions['plu_name'] = predictions['plu'].map(name_lookup)

        print(f"\n=== Predictions for {args.date} (Attendance: {args.attendance}) ===")
        print(predictions[['plu', 'plu_name', 'predicted_qty', 'method']].to_string(index=False))


if __name__ == '__main__':
    main()
