-- Q4: How do sales change month by month?
-- Uses the purchase date. LAG() gives month-over-month growth.
WITH monthly AS (
    SELECT order_month,
           SUM(item_revenue)        AS revenue,
           COUNT(DISTINCT order_id) AS orders
    FROM fact_orders
    WHERE is_valid_sale = 1 AND item_count > 0
    GROUP BY order_month
)
SELECT order_month,
       CAST(revenue AS NUMERIC(18,2))          AS revenue,
       orders,
       CAST(revenue / orders AS NUMERIC(10,2)) AS average_order_value,
       CAST(100.0 * (revenue - LAG(revenue) OVER (ORDER BY order_month))
            / LAG(revenue) OVER (ORDER BY order_month) AS NUMERIC(8,2)) AS mom_growth_pct
FROM monthly
ORDER BY order_month;
