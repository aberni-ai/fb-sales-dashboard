# F&B Item Sales Forecasting Tool

Sales forecasting and analysis tool for Canobie Lake Park food & beverage operations.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit dashboard
streamlit run src/app.py
```

## Data Pipeline

The data has been processed and is ready to use. If you need to rerun:

```bash
# 1. Ingest sales files and attendance data
python src/ingest.py

# 2. Add feature engineering columns
python src/features.py

# 3. Train forecasting model
python src/forecast.py --action train --model-type gbm
```

## Analysis Scripts

```bash
# View summary statistics
python src/analysis.py --report summary

# View top sellers
python src/analysis.py --report top

# View YoY trends
python src/analysis.py --report trends
```

## Forecasting

```bash
# Generate forecast for a specific date
python src/forecast.py --action predict --date 2026-06-15 --attendance 5000
```

## Data Summary

- **Files ingested:** 304 operating days
- **Records:** 103,362 item-day records
- **Unique items:** ~500+
- **Date range:** 2023-2025 seasons
- **Model R²:** 0.85

## File Structure

```
fb-forecasting/
├── data/
│   ├── sales/          # 610 daily sales Excel files
│   └── attendance.xlsx # Attendance data (2023-2025)
├── src/
│   ├── ingest.py       # Data ingestion
│   ├── features.py     # Feature engineering
│   ├── analysis.py     # Reports and analytics
│   ├── forecast.py     # ML forecasting model
│   └── app.py          # Streamlit dashboard
├── fb_sales.db         # SQLite database
├── forecast_model.pkl  # Trained model
└── requirements.txt
```
