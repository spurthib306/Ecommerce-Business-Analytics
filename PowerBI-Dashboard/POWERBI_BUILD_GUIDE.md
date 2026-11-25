# Power BI build guide

The pipeline produces everything Power BI needs, but a `.pbix` file can only be
created in **Power BI Desktop, which runs on Windows only**. Build it once with the
steps below (about 45 minutes), save it as `PowerBI-Dashboard/ecommerce_dashboard.pbix`,
and add screenshots to `PowerBI-Dashboard/screenshots/`.

`dashboard.html` in this folder is a working preview of the same report. It opens in any
browser on macOS or Windows and shows the layout and numbers to aim for.

## Where to run Power BI Desktop

| Your computer | Option |
|---|---|
| Windows 10/11 | Install **Power BI Desktop** free from the Microsoft Store. |
| Mac (Apple silicon or Intel) | Run Windows 11 in **Parallels Desktop** or **VMware Fusion**, then install Power BI Desktop inside it. Or use a Windows PC (university lab, a friend's laptop). |
| Mac, no Windows at all | Use `dashboard.html` for the dashboard and screenshots, and say so honestly in your README and interviews. Don't list Power BI on your resume until you have built the report yourself. |

## 1. Load the data

1. Run the pipeline (`run.bat` on Windows, `./run.sh` on Mac). It writes
   `PowerBI-Dashboard/model/fact_orders.csv` and `fact_order_items.csv`.
2. Power BI Desktop: **Home > Get data > Text/CSV**, load `fact_orders.csv`, then repeat for `fact_order_items.csv`.
3. In **Transform data (Power Query)** check the column types:
   - `order_month`, `order_purchase_timestamp`: Date / Date-time
   - `item_revenue`, `freight_value`, `price`: Fixed decimal number
   - `is_valid_sale`, `is_late`, `item_count`, `days_vs_estimate`, `delivery_days`: Whole number
   - `review_score`: Decimal number
   - every `*_id` column and `customer_state`: Text
   - Click **Close & Apply**.

   *Alternative:* if you loaded PostgreSQL (`SQL-Queries/00_postgres_setup.sql`), use
   **Get data > PostgreSQL database** and import the `fact_orders` and `fact_order_items` views.

## 2. Model

1. **Model view**: drag `fact_orders[order_id]` onto `fact_order_items[order_id]`.
   Cardinality is One-to-many. Set **Cross filter direction = Both**, so a Category slicer
   (from the items table) also filters order-level KPIs.
2. **Home > Enter data**, name the table `_Measures`, click Load. Add every measure in
   [`measures.dax`](measures.dax) with **Modeling > New measure**.
3. Format the measures: Revenue and Average Order Value as Currency (R$, 2 decimals),
   Late Delivery % and Revenue Share % as Percentage, Average Review Score with 2 decimals.

## 3. Apply the theme

**View > Themes > Browse for themes** and select [`theme.json`](theme.json).

## 4. Build the report page

| Area | Visual | Fields |
|---|---|---|
| KPI cards | 5 x Card (new) | Revenue, Orders, Average Order Value, Average Review Score, Late Delivery % |
| Monthly revenue | Line chart | X: `fact_orders[order_month]` (turn off the date hierarchy), Y: Revenue |
| Revenue by category | Clustered bar chart | Y: `fact_order_items[category]`, X: Revenue. Filter pane: Top N = 10 by Revenue |
| Regional performance | Clustered bar chart | Y: `customer_state`, X: Revenue, Top N = 10. A second bar for `customer_region` |
| Delivery vs reviews | Clustered column chart | X: `delivery_bucket`, Y: Average Review Score. Filter out (Blank) |
| Late deliveries | Clustered bar chart | Y: `customer_state`, X: Late Delivery %. Filter: delivered orders (COUNT of `is_late`) >= 50 |
| Order status | Bar chart (preferred) or donut | Y: `order_status`, X: All Orders (any status) |
| Slicers | Slicer x 4 | `order_month` (Between), `customer_region`, `customer_state`, `fact_order_items[category]` (Dropdown) |

Tips
- Give every visual a title that states the metric, e.g. "Monthly revenue (R$)".
- Use **Format > Edit interactions** to choose *highlight* or *filter* between visuals.
- Keep one number format per measure across the page.

## 5. Validate against SQL

With no slicers selected the cards must show exactly the SQL results
(`SQL-Queries/results/02_kpi_overview.csv`):

| Measure | Expected |
|---|---|
| Revenue | R$13,449,529.68 |
| Orders | 97,905 |
| Average Order Value | R$137.37 |
| Customers | 94,703 |
| Average Review Score | 4.12 |
| Late Delivery % | 6.79% |

Then test one slicer, e.g. Region = Northeast and Category = watches gifts. The
expected values are Revenue R$164,152.18, Orders 735 and AOV R$223.34 (the HTML dashboard shows the same).

## 6. Save and publish

- Save as `PowerBI-Dashboard/ecommerce_dashboard.pbix` (about 10-20 MB, fine for GitHub).
- Export screenshots (Windows: `Win + Shift + S`) to `PowerBI-Dashboard/screenshots/`.
- Optional: **File > Export > Export to PDF** for a static copy.
