-- =====================================================================
-- 01_create_views.sql
-- Two analysis views every other query reads from.
-- Portable SQL: runs unchanged on DuckDB (default) and PostgreSQL.
--
-- Definitions used throughout the project
--   Revenue      = SUM(order_items.price). Freight is reported separately.
--   Valid sale   = order_status NOT IN ('canceled', 'unavailable').
--   Scope        = orders purchased 2017-01-01 to 2018-08-31
--                  (20 complete months; 2016 and Sep/Oct 2018 are partial).
--   Late         = delivered date later than the estimated delivery date
--                  (compared as calendar dates, delivered orders only).
--   Review score = average score per order (547 orders have 2+ reviews).
-- =====================================================================

DROP VIEW IF EXISTS fact_order_items;
DROP VIEW IF EXISTS fact_orders;

-- One row per order. Items and reviews are aggregated to order level
-- BEFORE joining, so no one-to-many join can duplicate order values.
CREATE VIEW fact_orders AS
WITH item_totals AS (
    SELECT order_id,
           COUNT(*)           AS item_count,
           SUM(price)         AS item_revenue,
           SUM(freight_value) AS freight_value
    FROM order_items
    GROUP BY order_id
),
review_per_order AS (
    SELECT order_id, AVG(review_score) AS review_score
    FROM order_reviews
    GROUP BY order_id
),
base AS (
    SELECT o.order_id,
           c.customer_unique_id,
           c.customer_state,
           c.customer_region,
           o.order_status,
           o.order_purchase_timestamp,
           CAST(DATE_TRUNC('month', o.order_purchase_timestamp) AS DATE) AS order_month,
           CASE WHEN o.order_status IN ('canceled', 'unavailable') THEN 0 ELSE 1 END AS is_valid_sale,
           COALESCE(it.item_count, 0)    AS item_count,
           COALESCE(it.item_revenue, 0)  AS item_revenue,
           COALESCE(it.freight_value, 0) AS freight_value,
           CASE WHEN o.order_status = 'delivered'
                 AND o.order_delivered_customer_date IS NOT NULL
                THEN CAST(o.order_delivered_customer_date AS DATE)
                   - CAST(o.order_estimated_delivery_date AS DATE)
           END AS days_vs_estimate,
           CASE WHEN o.order_status = 'delivered'
                 AND o.order_delivered_customer_date IS NOT NULL
                THEN CAST(o.order_delivered_customer_date AS DATE)
                   - CAST(o.order_purchase_timestamp AS DATE)
           END AS delivery_days,
           r.review_score
    FROM orders AS o
    JOIN customers AS c          ON c.customer_id = o.customer_id
    LEFT JOIN item_totals AS it  ON it.order_id = o.order_id
    LEFT JOIN review_per_order r ON r.order_id = o.order_id
    WHERE o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
)
SELECT base.*,
       CASE WHEN days_vs_estimate IS NULL THEN NULL
            WHEN days_vs_estimate > 0 THEN 1 ELSE 0 END AS is_late,
       CASE WHEN days_vs_estimate IS NULL THEN NULL
            WHEN days_vs_estimate <= 0 THEN '1. On time or early'
            WHEN days_vs_estimate <= 3 THEN '2. 1-3 days late'
            WHEN days_vs_estimate <= 7 THEN '3. 4-7 days late'
            ELSE '4. 8+ days late' END AS delivery_bucket
FROM base;

-- One row per order item, carrying the order attributes and English category.
CREATE VIEW fact_order_items AS
SELECT oi.order_id,
       oi.order_item_id,
       oi.product_id,
       oi.seller_id,
       p.category,
       oi.price,
       oi.freight_value,
       fo.customer_unique_id,
       fo.customer_state,
       fo.customer_region,
       fo.order_status,
       fo.order_month,
       fo.is_valid_sale,
       fo.is_late,
       fo.review_score
FROM order_items AS oi
JOIN fact_orders AS fo ON fo.order_id = oi.order_id
JOIN products    AS p  ON p.product_id = oi.product_id;
