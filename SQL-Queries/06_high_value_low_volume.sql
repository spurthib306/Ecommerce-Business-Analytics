-- Which categories have high revenue but relatively low order volume?
-- A category "punches above its volume" when its share of revenue is at least
-- 1.5x its share of orders. Only categories with 300+ orders are compared,
-- so tiny categories cannot dominate the list by chance.
WITH cat AS (
    SELECT category,
           SUM(price)               AS revenue,
           COUNT(DISTINCT order_id) AS orders
    FROM fact_order_items
    WHERE is_valid_sale = 1
    GROUP BY category
),
shares AS (
    SELECT category, revenue, orders,
           100.0 * revenue / SUM(revenue) OVER () AS revenue_share,
           100.0 * orders  / SUM(orders)  OVER () AS order_share
    FROM cat
    WHERE orders >= 300
)
SELECT category,
       CAST(revenue AS NUMERIC(18,2))            AS revenue,
       orders,
       CAST(revenue / orders AS NUMERIC(10,2))   AS category_aov,
       CAST(revenue_share AS NUMERIC(6,2))       AS revenue_share_pct,
       CAST(order_share AS NUMERIC(6,2))         AS order_share_pct,
       CAST(revenue_share / order_share AS NUMERIC(6,2)) AS revenue_to_volume_ratio,
       CASE WHEN revenue_share >= 1.5 * order_share THEN 'High value, lower volume'
            WHEN revenue_share <= 0.67 * order_share THEN 'High volume, lower value'
            ELSE 'In line' END                   AS profile
FROM shares
ORDER BY revenue_to_volume_ratio DESC;
