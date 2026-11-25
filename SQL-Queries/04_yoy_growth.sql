-- Year-over-year: Jan-Aug 2018 vs the same eight months of 2017.
SELECT
    CAST(SUM(CASE WHEN order_month < '2017-09-01' THEN item_revenue ELSE 0 END) AS NUMERIC(18,2)) AS revenue_jan_aug_2017,
    CAST(SUM(CASE WHEN order_month >= '2018-01-01' THEN item_revenue ELSE 0 END) AS NUMERIC(18,2)) AS revenue_jan_aug_2018,
    COUNT(DISTINCT CASE WHEN order_month < '2017-09-01' THEN order_id END)  AS orders_jan_aug_2017,
    COUNT(DISTINCT CASE WHEN order_month >= '2018-01-01' THEN order_id END) AS orders_jan_aug_2018,
    CAST(100.0 * (SUM(CASE WHEN order_month >= '2018-01-01' THEN item_revenue ELSE 0 END)
                - SUM(CASE WHEN order_month < '2017-09-01' THEN item_revenue ELSE 0 END))
         / SUM(CASE WHEN order_month < '2017-09-01' THEN item_revenue ELSE 0 END) AS NUMERIC(8,2)) AS revenue_growth_pct
FROM fact_orders
WHERE is_valid_sale = 1 AND item_count > 0;
