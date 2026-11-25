"""Step 3 - load the cleaned CSVs into DuckDB and run every SQL file.

DuckDB is an embedded SQL database: it installs with pip and needs no server,
so this step works the same on macOS and Windows. The SQL files are written
in PostgreSQL-compatible syntax; see SQL-Queries/00_postgres_setup.sql to run
them on PostgreSQL instead.

Outputs
  Dataset/ecommerce.duckdb                 the database (open it with DBeaver or the duckdb CLI)
  SQL-Queries/results/<query>.csv           one result file per query
  SQL-Queries/results/00_import_row_counts.csv
  SQL-Queries/results/00_validation_checks.csv   SQL vs pandas cross-checks
  PowerBI-Dashboard/model/*.csv            model tables for Power BI
"""
import sys

import duckdb
import pandas as pd

from config import CLEAN_DIR, DB_PATH, PBI_MODEL_DIR, RESULTS_DIR, SCOPE_END_EXCLUSIVE, SCOPE_START, SQL_DIR, ensure_dirs

TABLES = ["customers", "orders", "order_items", "order_payments", "order_reviews", "products", "sellers"]
# Columns that must stay text (leading zeros in zip prefixes, hex IDs).
TEXT_TYPES = {
    "customer_id": "VARCHAR", "customer_unique_id": "VARCHAR", "customer_zip_code_prefix": "VARCHAR",
    "order_id": "VARCHAR", "product_id": "VARCHAR", "seller_id": "VARCHAR",
    "seller_zip_code_prefix": "VARCHAR", "review_id": "VARCHAR",
}


def load_tables(con):
    counts = []
    for t in TABLES:
        path = (CLEAN_DIR / f"{t}.csv").as_posix()
        header = pd.read_csv(CLEAN_DIR / f"{t}.csv", nrows=0).columns
        types = {c: v for c, v in TEXT_TYPES.items() if c in header}
        types_sql = "{" + ", ".join(f"'{c}': '{v}'" for c, v in types.items()) + "}"
        con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT * FROM read_csv('{path}', header = true, types = {types_sql})")
        db_rows = con.execute(f"SELECT COUNT(*) FROM {t}").fetchall()[0][0]
        csv_rows = sum(1 for _ in open(CLEAN_DIR / f"{t}.csv", encoding="utf-8")) - 1
        counts.append({"table": t, "csv_rows": csv_rows, "database_rows": db_rows,
                       "status": "OK" if csv_rows == db_rows else "CHECK"})
    return pd.DataFrame(counts)


def independent_checks(con):
    """Recompute headline numbers in pandas, without SQL, and compare."""
    orders = pd.read_csv(CLEAN_DIR / "orders.csv", parse_dates=["order_purchase_timestamp"])
    items = pd.read_csv(CLEAN_DIR / "order_items.csv")
    scope = orders[(orders.order_purchase_timestamp >= SCOPE_START)
                   & (orders.order_purchase_timestamp < SCOPE_END_EXCLUSIVE)
                   & ~orders.order_status.isin(["canceled", "unavailable"])]
    scoped_items = items[items.order_id.isin(scope.order_id)]
    pd_revenue = round(scoped_items.price.sum(), 2)
    pd_orders = scoped_items.order_id.nunique()

    kpi = con.execute("SELECT total_revenue, distinct_orders FROM read_csv(?)",
                      [(RESULTS_DIR / "02_kpi_overview.csv").as_posix()]).fetchall()[0]
    monthly_sum = con.execute("SELECT SUM(revenue) FROM read_csv(?)",
                              [(RESULTS_DIR / "03_monthly_revenue.csv").as_posix()]).fetchall()[0][0]
    cat_sum = con.execute("SELECT SUM(revenue) FROM read_csv(?)",
                          [(RESULTS_DIR / "05_category_revenue.csv").as_posix()]).fetchall()[0][0]
    state_sum = con.execute("SELECT SUM(revenue) FROM read_csv(?)",
                            [(RESULTS_DIR / "07_revenue_by_state.csv").as_posix()]).fetchall()[0][0]

    rows = [
        ("Total revenue: SQL KPI vs pandas", float(kpi[0]), pd_revenue),
        ("Distinct orders: SQL KPI vs pandas", float(kpi[1]), float(pd_orders)),
        ("Sum of monthly revenue vs KPI total", float(monthly_sum), float(kpi[0])),
        ("Sum of category revenue vs KPI total", float(cat_sum), float(kpi[0])),
        ("Sum of state revenue vs KPI total", float(state_sum), float(kpi[0])),
    ]
    out = pd.DataFrame(rows, columns=["check", "value_a", "value_b"])
    out["difference"] = (out.value_a - out.value_b).round(2)
    out["status"] = out.difference.abs().le(1.0).map({True: "MATCH", False: "CHECK"})
    return out


def main():
    ensure_dirs()
    if not (CLEAN_DIR / "orders.csv").exists():
        print("[sql] Cleaned data not found. Run step 2 first.")
        return 1
    try:
        DB_PATH.unlink(missing_ok=True)
    except PermissionError:
        print(f"[sql] {DB_PATH.name} is open in another program (e.g. DBeaver or Power BI). Close it and re-run.")
        return 1
    con = duckdb.connect(str(DB_PATH))
    try:
        counts = load_tables(con)
        counts.to_csv(RESULTS_DIR / "00_import_row_counts.csv", index=False)
        print(counts.to_string(index=False))

        sql_files = sorted(p for p in SQL_DIR.glob("*.sql") if p.name[:2].isdigit() and p.name[:2] != "00")
        for path in sql_files:
            sql = path.read_text(encoding="utf-8")
            if path.name.startswith("01_"):
                con.execute(sql)  # creates the views
                print(f"[sql] {path.name}: views created")
                continue
            df = con.execute(sql).df()
            df.to_csv(RESULTS_DIR / f"{path.stem}.csv", index=False, encoding="utf-8")
            print(f"[sql] {path.name}: {len(df)} rows")

        checks = independent_checks(con)
        checks.to_csv(RESULTS_DIR / "00_validation_checks.csv", index=False)
        print(checks.to_string(index=False))

        # Model tables for Power BI (one fact at order grain, one at item grain).
        for view in ("fact_orders", "fact_order_items"):
            target = (PBI_MODEL_DIR / f"{view}.csv").as_posix()
            con.execute(f"COPY (SELECT * FROM {view}) TO '{target}' (HEADER, DELIMITER ',')")
        print(f"[sql] Power BI model tables written to {PBI_MODEL_DIR}")
        if (checks.status != "MATCH").any() or (counts.status != "OK").any():
            print("[sql] WARNING: at least one validation check did not match")
            return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
