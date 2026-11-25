"""Shared paths and settings. Every path is built with pathlib so the same
code runs on macOS, Linux and Windows."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DATASET_DIR = ROOT / "Dataset"
RAW_DIR = DATASET_DIR / "raw"
CLEAN_DIR = DATASET_DIR / "cleaned"
SAMPLE_DIR = DATASET_DIR / "sample"
KAGGLE_CACHE = DATASET_DIR / ".kaggle_cache"
DB_PATH = DATASET_DIR / "ecommerce.duckdb"

SQL_DIR = ROOT / "SQL-Queries"
RESULTS_DIR = SQL_DIR / "results"
EXCEL_DIR = ROOT / "Excel-Analysis"
PBI_DIR = ROOT / "PowerBI-Dashboard"
PBI_MODEL_DIR = PBI_DIR / "model"
INSIGHTS_DIR = ROOT / "Insights"
CHARTS_DIR = INSIGHTS_DIR / "charts"

KAGGLE_DATASET = "olistbr/brazilian-ecommerce"
KAGGLE_URL = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"

# Raw file name -> cleaned table name
RAW_FILES = {
    "olist_customers_dataset.csv": "customers",
    "olist_orders_dataset.csv": "orders",
    "olist_order_items_dataset.csv": "order_items",
    "olist_order_payments_dataset.csv": "order_payments",
    "olist_order_reviews_dataset.csv": "order_reviews",
    "olist_products_dataset.csv": "products",
    "olist_sellers_dataset.csv": "sellers",
    "product_category_name_translation.csv": "category_translation",
    "olist_geolocation_dataset.csv": "geolocation",
}

# Analysis scope: the 20 complete months. 2016 has only ~330 orders spread
# over gaps, and Sep/Oct 2018 hold 20 orders (the extract was cut mid-month).
SCOPE_START = "2017-01-01"
SCOPE_END_EXCLUSIVE = "2018-09-01"


def ensure_dirs():
    for d in (RAW_DIR, CLEAN_DIR, SAMPLE_DIR, RESULTS_DIR, EXCEL_DIR,
              PBI_MODEL_DIR, INSIGHTS_DIR, CHARTS_DIR):
        d.mkdir(parents=True, exist_ok=True)
