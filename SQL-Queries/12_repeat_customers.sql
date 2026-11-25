-- Customer behaviour: how many customers come back?
-- customer_unique_id identifies a person; customer_id is issued per order.
WITH per_customer AS (
    SELECT customer_unique_id,
           COUNT(DISTINCT order_id) AS orders,
           SUM(item_revenue)        AS revenue
    FROM fact_orders
    WHERE is_valid_sale = 1 AND item_count > 0
    GROUP BY customer_unique_id
)
SELECT CASE WHEN orders = 1 THEN '1 order'
            WHEN orders = 2 THEN '2 orders'
            ELSE '3+ orders' END                                        AS customer_type,
       COUNT(*)                                                         AS customers,
       CAST(100.0 * COUNT(*) / SUM(COUNT(*)) OVER () AS NUMERIC(6,2))   AS customer_share_pct,
       CAST(SUM(revenue) AS NUMERIC(18,2))                              AS revenue,
       CAST(100.0 * SUM(revenue) / SUM(SUM(revenue)) OVER () AS NUMERIC(6,2)) AS revenue_share_pct
FROM per_customer
GROUP BY CASE WHEN orders = 1 THEN '1 order'
              WHEN orders = 2 THEN '2 orders'
              ELSE '3+ orders' END
ORDER BY customer_type;
