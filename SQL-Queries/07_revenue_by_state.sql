-- Q3: Which regions contribute the most revenue? (state level)
SELECT customer_state,
       customer_region,
       CAST(SUM(item_revenue) AS NUMERIC(18,2))                         AS revenue,
       COUNT(DISTINCT order_id)                                         AS orders,
       COUNT(DISTINCT customer_unique_id)                               AS customers,
       CAST(SUM(item_revenue) / COUNT(DISTINCT order_id) AS NUMERIC(10,2)) AS average_order_value,
       CAST(AVG(freight_value) AS NUMERIC(10,2))                        AS avg_freight_per_order,
       CAST(100.0 * SUM(item_revenue) / SUM(SUM(item_revenue)) OVER () AS NUMERIC(6,2)) AS revenue_share_pct
FROM fact_orders
WHERE is_valid_sale = 1 AND item_count > 0
GROUP BY customer_state, customer_region
ORDER BY revenue DESC;
