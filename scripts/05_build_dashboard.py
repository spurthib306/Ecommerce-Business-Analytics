"""Step 5 - build the interactive HTML dashboard (PowerBI-Dashboard/dashboard.html).

Power BI Desktop runs only on Windows, so this self-contained HTML file mirrors
the Power BI report spec (KPI cards, monthly line, category/state/region bars,
order status, date/region/state/category slicers) and opens offline in any
browser on macOS or Windows. Data is embedded as compact columnar arrays.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import pandas as pd

from config import DB_PATH, PBI_DIR, ensure_dirs

ASSETS = Path(__file__).resolve().parent / "dashboard"


def build_data(con):
    orders = con.execute("""
        SELECT order_id, customer_unique_id, customer_state, customer_region, order_status,
               strftime(order_month, '%Y-%m') AS ym, item_count,
               CAST(ROUND(item_revenue * 100) AS BIGINT) AS rev_cents,
               review_score, is_late, days_vs_estimate, delivery_days
        FROM fact_orders ORDER BY order_purchase_timestamp, order_id
    """).df()
    items = con.execute("""
        SELECT order_id, category, CAST(ROUND(price * 100) AS BIGINT) AS price_cents
        FROM fact_order_items
    """).df()

    months = sorted(orders.ym.unique())
    regions = sorted(orders.customer_region.unique())
    states = sorted(orders.customer_state.unique())
    state_region = orders.drop_duplicates("customer_state").set_index("customer_state").customer_region
    statuses = list(orders.order_status.value_counts().index)
    categories = sorted(items.category.unique())

    idx = lambda values: {v: i for i, v in enumerate(values)}
    m_i, s_i, st_i, c_i = idx(months), idx(states), idx(statuses), idx(categories)
    order_i = {oid: k for k, oid in enumerate(orders.order_id)}
    cust_i = {c: k for k, c in enumerate(orders.customer_unique_id.unique())}

    def as_int_list(series, missing):
        return [missing if pd.isna(v) else int(v) for v in series]

    data = {
        "months": months, "regions": regions, "states": states,
        "stateRegion": [regions.index(state_region[s]) for s in states],
        "statuses": statuses, "categories": categories,
        "orders": {
            "m": [m_i[v] for v in orders.ym],
            "s": [s_i[v] for v in orders.customer_state],
            "st": [st_i[v] for v in orders.order_status],
            "cu": [cust_i[v] for v in orders.customer_unique_id],
            "n": orders.item_count.astype(int).tolist(),
            "rev": orders.rev_cents.astype(int).tolist(),
            "rv": as_int_list((orders.review_score * 100).round(), -1),
            "lt": as_int_list(orders.is_late, -1),
            "dv": as_int_list(orders.days_vs_estimate, 0),
            "dd": as_int_list(orders.delivery_days, -1),
        },
        "items": {
            "o": [order_i[v] for v in items.order_id],
            "c": [c_i[v] for v in items.category],
            "p": items.price_cents.astype(int).tolist(),
        },
    }
    return data


def main():
    ensure_dirs()
    if not DB_PATH.exists():
        print("[dashboard] Database not found. Run step 3 first.")
        return 1
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        data = build_data(con)
    finally:
        con.close()
    html = (ASSETS / "template.html").read_text(encoding="utf-8")
    html = (html.replace("/*__CSS__*/", (ASSETS / "dashlib.css").read_text(encoding="utf-8"))
                .replace("/*__LIB__*/", (ASSETS / "dashlib.js").read_text(encoding="utf-8"))
                .replace("/*__APP__*/", (ASSETS / "app.js").read_text(encoding="utf-8"))
                .replace("__BUILT__", datetime.now().strftime("%d %b %Y"))
                .replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":"))))
    out = PBI_DIR / "dashboard.html"
    out.write_text(html, encoding="utf-8")
    print(f"[dashboard] {out} ({out.stat().st_size / 1e6:.1f} MB) - open it in any browser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
