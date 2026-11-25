-- Validation: item price + freight should reconcile with payments.
-- Differences come from vouchers, instalment interest and rounding.
WITH paid AS (
    SELECT order_id, SUM(payment_value) AS paid
    FROM order_payments
    GROUP BY order_id
)
SELECT CAST(SUM(fo.item_revenue + fo.freight_value) AS NUMERIC(18,2)) AS items_plus_freight,
       CAST(SUM(pd.paid) AS NUMERIC(18,2))                            AS payments_received,
       CAST(100.0 * (SUM(pd.paid) - SUM(fo.item_revenue + fo.freight_value))
            / SUM(fo.item_revenue + fo.freight_value) AS NUMERIC(6,3)) AS difference_pct,
       CAST(SUM(CASE WHEN pd.paid IS NULL THEN 1 ELSE 0 END) AS INTEGER) AS orders_without_payment
FROM fact_orders AS fo
LEFT JOIN paid AS pd ON pd.order_id = fo.order_id
WHERE fo.is_valid_sale = 1 AND fo.item_count > 0;
