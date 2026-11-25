-- Q6: Are delivery delays associated with lower customer review scores?
-- Delivered orders that have a review, grouped by how late they arrived.
SELECT delivery_bucket,
       COUNT(*)                                                               AS orders,
       CAST(AVG(review_score) AS NUMERIC(4,2))                                AS avg_review,
       CAST(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC(5,2)) AS pct_1_2_star,
       CAST(100.0 * SUM(CASE WHEN review_score = 5 THEN 1 ELSE 0 END) / COUNT(*) AS NUMERIC(5,2))  AS pct_5_star
FROM fact_orders
WHERE delivery_bucket IS NOT NULL
  AND review_score IS NOT NULL
GROUP BY delivery_bucket
ORDER BY delivery_bucket;
