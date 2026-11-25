-- Q2: Which product categories generate the highest sales?
-- Item-level view, so revenue is the item price in each category.
-- Category AOV = category revenue / orders that contain the category.
WITH cat AS (
    SELECT category,
           SUM(price)               AS revenue,
           COUNT(DISTINCT order_id) AS orders,
           COUNT(*)                 AS items,
           AVG(price)               AS avg_item_price,
           AVG(review_score)        AS avg_review
    FROM fact_order_items
    WHERE is_valid_sale = 1
    GROUP BY category
)
SELECT RANK() OVER (ORDER BY revenue DESC)                        AS revenue_rank,
       category,
       CAST(revenue AS NUMERIC(18,2))                             AS revenue,
       orders,
       items,
       CAST(revenue / orders AS NUMERIC(10,2))                    AS category_aov,
       CAST(avg_item_price AS NUMERIC(10,2))                      AS avg_item_price,
       CAST(avg_review AS NUMERIC(4,2))                           AS avg_review,
       CAST(100.0 * revenue / SUM(revenue) OVER () AS NUMERIC(6,2)) AS revenue_share_pct
FROM cat
ORDER BY revenue DESC;
