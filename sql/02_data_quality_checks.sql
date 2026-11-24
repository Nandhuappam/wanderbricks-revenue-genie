-- =====================================================================
-- Data-quality checks for the Revenue & Booking Analyst
-- A) Run on the SOURCE before building Gold; record the results in the PR
-- B) Run on GOLD after building; every check should return 0 / pass
-- =====================================================================

-- ---------- A. Source profiling (samples.wanderbricks) ----------

-- A1. Row counts per table
SELECT 'bookings' AS tbl, COUNT(*) AS rows FROM samples.wanderbricks.bookings
UNION ALL SELECT 'properties',   COUNT(*) FROM samples.wanderbricks.properties
UNION ALL SELECT 'destinations', COUNT(*) FROM samples.wanderbricks.destinations
UNION ALL SELECT 'users',        COUNT(*) FROM samples.wanderbricks.users
UNION ALL SELECT 'hosts',        COUNT(*) FROM samples.wanderbricks.hosts;

-- A2. Which status values really exist? (confirm the revenue rule)
SELECT status, COUNT(*) AS bookings, SUM(total_amount) AS amount
FROM samples.wanderbricks.bookings
GROUP BY status ORDER BY bookings DESC;

-- A3. Bad rows that the Gold layer will drop
SELECT
  SUM(CASE WHEN total_amount IS NULL      THEN 1 ELSE 0 END) AS null_amount,
  SUM(CASE WHEN total_amount < 0          THEN 1 ELSE 0 END) AS negative_amount,
  SUM(CASE WHEN check_out <= check_in     THEN 1 ELSE 0 END) AS bad_stay_dates,
  COUNT(*) - COUNT(DISTINCT booking_id)                      AS duplicate_booking_ids
FROM samples.wanderbricks.bookings;

-- A4. Orphan keys (bookings with no matching property or user)
SELECT
  SUM(CASE WHEN p.property_id IS NULL THEN 1 ELSE 0 END) AS orphan_property,
  SUM(CASE WHEN u.user_id     IS NULL THEN 1 ELSE 0 END) AS orphan_user
FROM samples.wanderbricks.bookings b
LEFT JOIN samples.wanderbricks.properties p ON b.property_id = p.property_id
LEFT JOIN samples.wanderbricks.users      u ON b.user_id     = u.user_id;

-- A5. Data freshness (state this "as of" date in the Genie instructions)
SELECT MIN(check_in) AS first_stay, MAX(check_in) AS last_stay,
       MAX(updated_at) AS data_as_of
FROM samples.wanderbricks.bookings;

-- ---------- B. Gold validation (wanderbricks_genie.gold) ----------

-- B1. No duplicates, no invalid stays
SELECT COUNT(*) - COUNT(DISTINCT booking_id) AS dup_ids,
       SUM(CASE WHEN nights <= 0 THEN 1 ELSE 0 END) AS bad_nights
FROM wanderbricks_genie.gold.fact_bookings;

-- B2. Revenue reconciles: confirmed_revenue equals the confirmed-only sum
SELECT
  SUM(confirmed_revenue)                                   AS gold_revenue,
  SUM(CASE WHEN status = 'confirmed' THEN total_amount END) AS check_revenue
FROM wanderbricks_genie.gold.fact_bookings;

-- B3. Wide view keeps every fact row (no join fan-out)
SELECT
  (SELECT COUNT(*) FROM wanderbricks_genie.gold.fact_bookings)     AS fact_rows,
  (SELECT COUNT(*) FROM wanderbricks_genie.gold.v_booking_revenue) AS wide_rows;
