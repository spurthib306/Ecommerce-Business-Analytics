-- Q1: What is the total sales revenue represented in the dataset?
-- Headline KPIs for valid sales in the analysis scope.
SELECT
    CAST(SUM(item_revenue) AS NUMERIC(18,2))                          AS total_revenue,
    CAST(SUM(freight_value) AS NUMERIC(18,2))                         AS total_freight,
    COUNT(DISTINCT order_id)                                          AS distinct_orders,
    -- AOV denominator: distinct valid orders that contain at least one item
    CAST(SUM(item_revenue) / COUNT(DISTINCT order_id) AS NUMERIC(18,2)) AS average_order_value,
    COUNT(DISTINCT customer_unique_id)                                AS distinct_customers,
    CAST(SUM(item_count) AS INTEGER)                                  AS items_sold,
    CAST(AVG(review_score) AS NUMERIC(4,2))                           AS avg_review_score,
    CAST(100.0 * SUM(is_late) / COUNT(is_late) AS NUMERIC(5,2))       AS late_delivery_pct,
    CAST(AVG(delivery_days) AS NUMERIC(5,1))                          AS avg_delivery_days
FROM fact_orders
WHERE is_valid_sale = 1
  AND item_count > 0;
