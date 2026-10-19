-- a) Order totals
-- Output:
--   total_orders | total_revenue | avg_order_value
--   180          | 99860.20      | 554.78
SELECT COUNT(*) AS total_orders,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_revenue,
       ROUND(AVG(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS avg_order_value
FROM orders o
JOIN products p ON o.product_id = p.product_id;

-- b) COUNT(*) vs COUNT(column)
-- Output: 180 | 165 | 15
SELECT COUNT(*) AS all_rows,
       COUNT(rating) AS rated,
       COUNT(*) - COUNT(rating) AS unrated
FROM orders;

-- c) LEFT JOIN with a genuine zero-match row
-- Output: C045 Vihaan
SELECT c.customer_id, c.name
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.name
HAVING COUNT(o.order_id) = 0;

-- Confirmation with NOT IN. Output: C045 Vihaan
SELECT customer_id, name
FROM customers
WHERE customer_id NOT IN (SELECT DISTINCT customer_id FROM orders);

-- (d) GROUP BY + HAVING
-- Output: Jaipur 19 8 42.1 | Lucknow 49 15 30.6 | Bangalore 33 8 24.2
SELECT c.city,
       COUNT(*) AS total_orders,
       SUM(o.returned) AS returned_orders,
       ROUND(100.0 * SUM(o.returned) / COUNT(*), 1) AS return_rate_pct
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.city
HAVING return_rate_pct > 20
ORDER BY return_rate_pct DESC;

-- e) Ranking with ORDER BY + LIMIT/OFFSET
-- Ties on total_spend are broken by customer_id ASC so the ranking is
-- deterministic and LIMIT/OFFSET pages return the same rows every run.
-- Output: C043|Reyansh|12920.0, C026|Isha|8371.6, C008|Meera|4564.6, C011|Arjun|4111.0, C042|Sanya|3785.0
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN products p  ON o.product_id  = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 5;

-- Ranks 3–5 without re-deriving the top 5. Should match the last three rows above.
-- Output: C008|Meera|4564.6, C011|Arjun|4111.0, C042|Sanya|3785.0
SELECT c.customer_id, c.name,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS total_spend
FROM orders o
JOIN products p  ON o.product_id  = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.name
ORDER BY total_spend DESC, c.customer_id ASC
LIMIT 3 OFFSET 2;

--f) Three-table JOIN with GROUP BY
-- Output: Haircare 54 44956.10 | Skincare 60 27346.00 | Babycare 30 16805.00 | PersonalCare 36 10753.10
SELECT p.category,
       COUNT(*) AS order_count,
       ROUND(SUM(o.quantity * p.price * (1 - COALESCE(o.discount_pct, 0) / 100.0)), 2) AS category_revenue
FROM orders o
JOIN products  p ON o.product_id  = p.product_id
JOIN customers c ON o.customer_id = c.customer_id
GROUP BY p.category
ORDER BY category_revenue DESC;

-- g) LIKE pattern match
-- Output: 10 rows
SELECT customer_id, name FROM customers WHERE name LIKE 'A%';

--h) DISTINCT
-- Output: Ad, Organic, Referral, Social
SELECT DISTINCT acquisition_source FROM customers ORDER BY acquisition_source;

--i) ALTER TABLE + UPDATE with CASE
ALTER TABLE customers ADD COLUMN loyalty_tier VARCHAR(10);

UPDATE customers
SET loyalty_tier = CASE WHEN city_tier = 1 THEN 'Gold' ELSE 'Silver' END;

-- Output: Gold 28 | Silver 17
SELECT loyalty_tier, COUNT(*) FROM customers GROUP BY loyalty_tier;