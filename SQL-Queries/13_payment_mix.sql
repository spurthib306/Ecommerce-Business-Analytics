-- Payment methods used (payments are a separate one-to-many table,
-- so they are summarised on their own, never joined into revenue).
SELECT p.payment_type,
       COUNT(DISTINCT p.order_id)                                         AS orders,
       CAST(SUM(p.payment_value) AS NUMERIC(18,2))                        AS payment_value,
       CAST(100.0 * SUM(p.payment_value) / SUM(SUM(p.payment_value)) OVER () AS NUMERIC(6,2)) AS value_share_pct,
       CAST(AVG(p.payment_installments) AS NUMERIC(5,2))                  AS avg_installments
FROM order_payments AS p
JOIN fact_orders AS fo ON fo.order_id = p.order_id
WHERE fo.is_valid_sale = 1
GROUP BY p.payment_type
ORDER BY payment_value DESC;
