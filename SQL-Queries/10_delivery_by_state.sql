-- Q5: How frequently are orders delivered later than estimated?
-- Which states have a higher share of delayed deliveries?
-- Delivered orders with a recorded delivery date only.
SELECT customer_state,
       customer_region,
       COUNT(*)                                             AS delivered_orders,
       CAST(SUM(is_late) AS INTEGER)                        AS late_orders,
       CAST(100.0 * SUM(is_late) / COUNT(*) AS NUMERIC(5,2)) AS late_delivery_pct,
       CAST(AVG(delivery_days) AS NUMERIC(5,1))             AS avg_delivery_days,
       CAST(AVG(review_score) AS NUMERIC(4,2))              AS avg_review
FROM fact_orders
WHERE is_late IS NOT NULL
GROUP BY customer_state, customer_region
ORDER BY late_delivery_pct DESC;
