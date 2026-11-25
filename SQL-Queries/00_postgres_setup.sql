-- =====================================================================
-- 00_postgres_setup.sql  (OPTIONAL - only if you want PostgreSQL)
--
-- The pipeline uses DuckDB by default (no server to install). To run the
-- same analysis in PostgreSQL instead:
--   1. Run the pipeline once so Dataset/cleaned/ exists.
--   2. createdb olist
--   3. From the project root (the folder containing Dataset/):
--        macOS:   psql -d olist -f SQL-Queries/00_postgres_setup.sql
--        Windows: psql -U postgres -d olist -f SQL-Queries/00_postgres_setup.sql
--   4. Run 01_create_views.sql, then any of the numbered queries.
-- \copy reads the files from your machine, so no server file access is needed.
-- =====================================================================

DROP VIEW IF EXISTS fact_order_items;
DROP VIEW IF EXISTS fact_orders;
DROP TABLE IF EXISTS order_reviews, order_payments, order_items, orders, products, sellers, customers;

CREATE TABLE customers (
    customer_id              VARCHAR(32) PRIMARY KEY,
    customer_unique_id       VARCHAR(32) NOT NULL,
    customer_zip_code_prefix VARCHAR(5),
    customer_city            TEXT,
    customer_state           CHAR(2),
    customer_region          TEXT
);

CREATE TABLE orders (
    order_id                      VARCHAR(32) PRIMARY KEY,
    customer_id                   VARCHAR(32) REFERENCES customers (customer_id),
    order_status                  TEXT,
    order_purchase_timestamp      TIMESTAMP,
    order_approved_at             TIMESTAMP,
    order_delivered_carrier_date  TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP
);

CREATE TABLE products (
    product_id                 VARCHAR(32) PRIMARY KEY,
    product_category_name      TEXT,
    product_name_length        NUMERIC,
    product_description_length NUMERIC,
    product_photos_qty         NUMERIC,
    product_weight_g           NUMERIC,
    product_length_cm          NUMERIC,
    product_height_cm          NUMERIC,
    product_width_cm           NUMERIC,
    category                   TEXT
);

CREATE TABLE sellers (
    seller_id              VARCHAR(32) PRIMARY KEY,
    seller_zip_code_prefix VARCHAR(5),
    seller_city            TEXT,
    seller_state           CHAR(2)
);

CREATE TABLE order_items (
    order_id            VARCHAR(32) REFERENCES orders (order_id),
    order_item_id       INTEGER,
    product_id          VARCHAR(32) REFERENCES products (product_id),
    seller_id           VARCHAR(32) REFERENCES sellers (seller_id),
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(10,2),
    freight_value       NUMERIC(10,2),
    PRIMARY KEY (order_id, order_item_id)
);

CREATE TABLE order_payments (
    order_id             VARCHAR(32) REFERENCES orders (order_id),
    payment_sequential   INTEGER,
    payment_type         TEXT,
    payment_installments INTEGER,
    payment_value        NUMERIC(10,2),
    PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE order_reviews (
    review_id               VARCHAR(32),
    order_id                VARCHAR(32) REFERENCES orders (order_id),
    review_score            INTEGER,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    has_comment             INTEGER,
    PRIMARY KEY (review_id, order_id)
);

\copy customers      FROM 'Dataset/cleaned/customers.csv'      WITH (FORMAT csv, HEADER true)
\copy orders         FROM 'Dataset/cleaned/orders.csv'         WITH (FORMAT csv, HEADER true)
\copy products       FROM 'Dataset/cleaned/products.csv'       WITH (FORMAT csv, HEADER true)
\copy sellers        FROM 'Dataset/cleaned/sellers.csv'        WITH (FORMAT csv, HEADER true)
\copy order_items    FROM 'Dataset/cleaned/order_items.csv'    WITH (FORMAT csv, HEADER true)
\copy order_payments FROM 'Dataset/cleaned/order_payments.csv' WITH (FORMAT csv, HEADER true)
\copy order_reviews  FROM 'Dataset/cleaned/order_reviews.csv'  WITH (FORMAT csv, HEADER true)

-- Row-count check after import (compare with SQL-Queries/results/00_import_row_counts.csv)
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers;
