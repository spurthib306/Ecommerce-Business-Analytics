-- Order status mix (all orders in scope, including canceled).
SELECT order_status,
       COUNT(*)                                                 AS orders,
       CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC(6,2)) AS share_pct
FROM fact_orders
GROUP BY order_status
ORDER BY orders DESC;
