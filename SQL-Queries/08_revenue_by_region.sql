-- Q3: Which regions contribute the most revenue? (macro-region level)
SELECT customer_region,
       CAST(SUM(item_revenue) AS NUMERIC(18,2))                         AS revenue,
       COUNT(DISTINCT order_id)                                         AS orders,
       CAST(SUM(item_revenue) / COUNT(DISTINCT order_id) AS NUMERIC(10,2)) AS average_order_value,
       CAST(100.0 * SUM(item_revenue) / SUM(SUM(item_revenue)) OVER () AS NUMERIC(6,2)) AS revenue_share_pct,
       CAST(100.0 * SUM(is_late) / COUNT(is_late) AS NUMERIC(5,2))      AS late_delivery_pct,
       CAST(AVG(delivery_days) AS NUMERIC(5,1))                         AS avg_delivery_days
FROM fact_orders
WHERE is_valid_sale = 1 AND item_count > 0
GROUP BY customer_region
ORDER BY revenue DESC;
