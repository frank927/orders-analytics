DROP VIEW IF EXISTS monthly_sales;

CREATE VIEW monthly_sales AS
SELECT
    SUBSTR(date, 1, 7) AS month,
    country,
    COUNT(*) AS order_count,
    SUM(amount_cents) AS total_sales_cents,
    ROUND(SUM(amount_cents) / 100.0, 2) AS total_sales_eur
FROM orders
WHERE status = 'completed'
GROUP BY
    SUBSTR(date, 1, 7),
    country;


DROP VIEW IF EXISTS top_customers;

CREATE VIEW top_customers AS
SELECT
    customer,
    COUNT(*) AS order_count,
    SUM(amount_cents) AS total_sales_cents,
    ROUND(SUM(amount_cents) / 100.0, 2) AS total_sales_eur
FROM orders
WHERE status = 'completed'
GROUP BY customer
ORDER BY
    total_sales_cents DESC,
    customer ASC
LIMIT 10;