"""Step 2 - profile and clean the raw Olist tables.

Outputs
  Dataset/cleaned/<table>.csv         cleaned copies (raw files untouched)
  Dataset/cleaned/data_quality_profile.csv   one row per raw table
  Dataset/cleaned/cleaning_log.csv     every change made, with row counts
  Dataset/sample/<table>.csv           1,000-order sample safe to commit to GitHub

Design choices (also documented in README.md):
  * IDs and zip prefixes are read as text so leading zeros survive.
  * Nothing is merged here. Tables stay at their own grain; joins happen in SQL
    so one-to-many joins cannot silently inflate revenue.
  * Rows are flagged, not deleted, unless they are exact duplicates.
"""
import sys

import pandas as pd

from config import CLEAN_DIR, RAW_DIR, RAW_FILES, SAMPLE_DIR, SCOPE_END_EXCLUSIVE, SCOPE_START, ensure_dirs

# Grain and primary key of each raw table (checked below, not assumed).
GRAIN = {
    "customers": ("one row per customer_id (one per order; the person is customer_unique_id)", ["customer_id"]),
    "orders": ("one row per order", ["order_id"]),
    "order_items": ("one row per item within an order", ["order_id", "order_item_id"]),
    "order_payments": ("one row per payment instalment record of an order", ["order_id", "payment_sequential"]),
    "order_reviews": ("one row per review of an order", ["review_id", "order_id"]),
    "products": ("one row per product", ["product_id"]),
    "sellers": ("one row per seller", ["seller_id"]),
    "category_translation": ("one row per Portuguese category name", ["product_category_name"]),
    "geolocation": ("one row per zip prefix / lat-lng observation (many per prefix)", None),
}

TEXT_COLS = {
    "customer_id", "customer_unique_id", "customer_zip_code_prefix", "order_id", "product_id",
    "seller_id", "seller_zip_code_prefix", "review_id", "geolocation_zip_code_prefix",
}

DATE_COLS = {
    "orders": ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
               "order_delivered_customer_date", "order_estimated_delivery_date"],
    "order_items": ["shipping_limit_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
}

REGION_BY_STATE = {
    **dict.fromkeys(["AC", "AP", "AM", "PA", "RO", "RR", "TO"], "North"),
    **dict.fromkeys(["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"], "Northeast"),
    **dict.fromkeys(["DF", "GO", "MT", "MS"], "Center-West"),
    **dict.fromkeys(["ES", "MG", "RJ", "SP"], "Southeast"),
    **dict.fromkeys(["PR", "RS", "SC"], "South"),
}

# Two categories exist in products but not in the translation file.
EXTRA_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_food_preparers",
}

log_rows = []


def log(table, step, rows_affected, note):
    log_rows.append({"table": table, "step": step, "rows_affected": int(rows_affected), "note": note})


def read_raw(name):
    file = next(f for f, t in RAW_FILES.items() if t == name)
    header = pd.read_csv(RAW_DIR / file, nrows=0).columns
    dtypes = {c: "string" for c in header if c in TEXT_COLS}
    return pd.read_csv(RAW_DIR / file, dtype=dtypes, encoding="utf-8")


def profile(name, df):
    grain, key = GRAIN[name]
    nulls = df.isna().sum()
    null_desc = "; ".join(f"{c}: {n:,}" for c, n in nulls.items() if n) or "none"
    return {
        "table": name,
        "rows": len(df),
        "columns": df.shape[1],
        "grain": grain,
        "primary_key": ", ".join(key) if key else "(none)",
        "duplicate_key_rows": int(df.duplicated(subset=key).sum()) if key else None,
        "exact_duplicate_rows": int(df.duplicated().sum()),
        "null_cells": int(nulls.sum()),
        "columns_with_nulls": null_desc,
    }


def strip_strings(name, df):
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()
    return df


def parse_dates(name, df):
    for col in DATE_COLS.get(name, []):
        before = df[col].notna().sum()
        df[col] = pd.to_datetime(df[col], errors="coerce", format="%Y-%m-%d %H:%M:%S")
        bad = before - df[col].notna().sum()
        log(name, f"parse {col} as datetime", bad, "values that failed to parse (set to empty)")
    return df


def clean_customers(df):
    df["customer_city"] = df["customer_city"].str.lower()
    df["customer_state"] = df["customer_state"].str.upper()
    df["customer_region"] = df["customer_state"].map(REGION_BY_STATE)
    log("customers", "add customer_region", df["customer_region"].notna().sum(),
        "Brazilian macro-region (IBGE) derived from state")
    unmapped = df["customer_region"].isna().sum()
    if unmapped:
        log("customers", "unmapped state", unmapped, "state not in region map")
    return df


def clean_orders(df):
    in_scope = (df["order_purchase_timestamp"] >= SCOPE_START) & (df["order_purchase_timestamp"] < SCOPE_END_EXCLUSIVE)
    log("orders", "analysis scope flag", (~in_scope).sum(),
        f"orders outside {SCOPE_START}..{SCOPE_END_EXCLUSIVE} (incomplete months); kept in the table, excluded by the SQL views")
    no_date = (df["order_status"] == "delivered") & df["order_delivered_customer_date"].isna()
    log("orders", "delivered without delivery date", no_date.sum(),
        "kept; excluded from delivery-delay metrics because the delay cannot be measured")
    neg = df["order_delivered_customer_date"] < df["order_purchase_timestamp"]
    log("orders", "check delivery before purchase", neg.sum(), "impossible dates; none expected")
    return df


def clean_order_items(df):
    bad = (df["price"] <= 0) | (df["freight_value"] < 0)
    log("order_items", "check price > 0 and freight >= 0", bad.sum(), "invalid numeric values")
    return df[~bad]


def clean_payments(df):
    zero = df["payment_value"] <= 0
    log("order_payments", "zero-value payment records", zero.sum(),
        "kept (voucher/instalment artefacts); they add nothing to totals")
    nd = df["payment_type"] == "not_defined"
    log("order_payments", "payment_type = not_defined", nd.sum(), "kept; labelled not_defined")
    return df


def clean_reviews(df):
    df["has_comment"] = df["review_comment_message"].notna().astype(int)
    df = df.drop(columns=["review_comment_title", "review_comment_message"])
    log("order_reviews", "drop free-text comment columns", len(df),
        "multi-line Portuguese text breaks CSV imports in Excel/PostgreSQL; replaced by has_comment flag")
    multi = df.duplicated(subset=["order_id"], keep=False)
    log("order_reviews", "orders with more than one review", df.loc[multi, "order_id"].nunique(),
        "kept; SQL averages scores per order")
    return df


def clean_products(df, translation):
    df = df.rename(columns={"product_name_lenght": "product_name_length",
                            "product_description_lenght": "product_description_length"})
    log("products", "rename misspelled columns", 2, "*_lenght -> *_length")
    missing = df["product_category_name"].isna()
    df["product_category_name"] = df["product_category_name"].fillna("unknown")
    log("products", "missing category -> 'unknown'", missing.sum(), "kept so their sales still count")
    mapping = dict(zip(translation["product_category_name"], translation["product_category_name_english"]))
    mapping.update(EXTRA_TRANSLATIONS)
    mapping["unknown"] = "unknown"
    untranslated = ~df["product_category_name"].isin(mapping.keys())
    df["category"] = df["product_category_name"].map(mapping).fillna(df["product_category_name"])
    df["category"] = df["category"].str.lower().str.replace("_", " ", regex=False)
    log("products", "add English category", len(df),
        f"from translation file + {len(EXTRA_TRANSLATIONS)} manual translations; {untranslated.sum()} left untranslated")
    return df


def clean_sellers(df):
    df["seller_city"] = df["seller_city"].str.lower()
    df["seller_state"] = df["seller_state"].str.upper()
    return df


def write_sample(tables, n_orders=1000):
    orders = tables["orders"]
    scope = orders[(orders["order_purchase_timestamp"] >= SCOPE_START)
                   & (orders["order_purchase_timestamp"] < SCOPE_END_EXCLUSIVE)]
    ids = set(scope.sample(n=min(n_orders, len(scope)), random_state=42)["order_id"])
    s = {"orders": orders[orders["order_id"].isin(ids)]}
    for t in ("order_items", "order_payments", "order_reviews"):
        s[t] = tables[t][tables[t]["order_id"].isin(ids)]
    s["customers"] = tables["customers"][tables["customers"]["customer_id"].isin(s["orders"]["customer_id"])]
    s["products"] = tables["products"][tables["products"]["product_id"].isin(s["order_items"]["product_id"])]
    s["sellers"] = tables["sellers"][tables["sellers"]["seller_id"].isin(s["order_items"]["seller_id"])]
    for name, df in s.items():
        df.to_csv(SAMPLE_DIR / f"{name}.csv", index=False, encoding="utf-8")


def main():
    ensure_dirs()
    missing = [f for f in RAW_FILES if not (RAW_DIR / f).exists()]
    if missing:
        print(f"[clean] Raw files missing: {missing}. Run step 1 first.")
        return 1

    raw = {name: read_raw(name) for name in RAW_FILES.values()}
    profiles = [profile(name, df) for name, df in raw.items()]
    pd.DataFrame(profiles).astype({"duplicate_key_rows": "Int64"}).to_csv(
        CLEAN_DIR / "data_quality_profile.csv", index=False, encoding="utf-8")

    t = {}
    for name in ("customers", "orders", "order_items", "order_payments", "order_reviews", "products", "sellers"):
        df = raw[name].copy()
        df = strip_strings(name, df)
        df = parse_dates(name, df)
        exact = df.duplicated().sum()
        if exact:
            df = df.drop_duplicates()
        log(name, "remove exact duplicate rows", exact, "rows identical in every column")
        t[name] = df

    t["customers"] = clean_customers(t["customers"])
    t["orders"] = clean_orders(t["orders"])
    t["order_items"] = clean_order_items(t["order_items"])
    t["order_payments"] = clean_payments(t["order_payments"])
    t["order_reviews"] = clean_reviews(t["order_reviews"])
    t["products"] = clean_products(t["products"], raw["category_translation"])
    t["sellers"] = clean_sellers(t["sellers"])
    log("geolocation", "not used", len(raw["geolocation"]),
        "1M rows, many per zip prefix; state-level analysis uses customers.customer_state instead")

    # Referential integrity: every child key should exist in its parent.
    orphan_items = ~t["order_items"]["order_id"].isin(t["orders"]["order_id"])
    log("order_items", "check order_id exists in orders", orphan_items.sum(), "orphan rows")
    orphan_prod = ~t["order_items"]["product_id"].isin(t["products"]["product_id"])
    log("order_items", "check product_id exists in products", orphan_prod.sum(), "orphan rows")
    orphan_cust = ~t["orders"]["customer_id"].isin(t["customers"]["customer_id"])
    log("orders", "check customer_id exists in customers", orphan_cust.sum(), "orphan rows")
    no_items = ~t["orders"]["order_id"].isin(t["order_items"]["order_id"])
    log("orders", "orders with no items", no_items.sum(),
        "mostly canceled/unavailable; contribute zero revenue")

    for name, df in t.items():
        df.to_csv(CLEAN_DIR / f"{name}.csv", index=False, encoding="utf-8", date_format="%Y-%m-%d %H:%M:%S")
        print(f"[clean] {name:<15} {len(df):>8,} rows -> {CLEAN_DIR / (name + '.csv')}")

    pd.DataFrame(log_rows).to_csv(CLEAN_DIR / "cleaning_log.csv", index=False, encoding="utf-8")
    write_sample(t)
    print(f"[clean] Cleaning log: {len(log_rows)} entries; 1,000-order sample written to {SAMPLE_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
