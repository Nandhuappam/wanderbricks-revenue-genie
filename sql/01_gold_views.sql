-- =====================================================================
-- Revenue & Booking Analyst: Gold layer on samples.wanderbricks
-- Source : samples.wanderbricks (read-only Unity Catalog sample)
-- Target : wanderbricks_genie.gold (change the catalog name if needed)
-- Purpose: clean, PII-free, Genie-friendly views
-- =====================================================================

CREATE CATALOG IF NOT EXISTS wanderbricks_genie;
CREATE SCHEMA  IF NOT EXISTS wanderbricks_genie.gold
  COMMENT 'Curated Gold views for the Revenue & Booking Analyst Genie agent';

USE CATALOG wanderbricks_genie;
USE SCHEMA gold;

-- ---------------------------------------------------------------------
-- 1. fact_bookings: cleaned booking fact
--    * dedupe on booking_id (keep latest updated_at)
--    * normalise status to lower-case/trimmed
--    * drop invalid stays (check_out <= check_in) and null/negative amounts
--    * add derived columns used by the business rules
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW fact_bookings
COMMENT 'One row per valid booking. Revenue = confirmed_revenue (status = confirmed only).'
AS
WITH dedup AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY booking_id ORDER BY updated_at DESC) AS rn
  FROM samples.wanderbricks.bookings
)
SELECT
  booking_id,
  user_id,
  property_id,
  check_in                                                   AS stay_start_date,
  check_out                                                  AS stay_end_date,
  DATEDIFF(check_out, check_in)                              AS nights,
  guests_count,
  CAST(total_amount AS DECIMAL(18,2))                        AS total_amount,
  LOWER(TRIM(status))                                        AS status,
  LOWER(TRIM(status)) = 'confirmed'                          AS is_confirmed,
  CASE WHEN LOWER(TRIM(status)) = 'confirmed'
       THEN CAST(total_amount AS DECIMAL(18,2)) ELSE 0 END   AS confirmed_revenue,
  CAST(created_at AS DATE)                                   AS booking_date,
  created_at                                                 AS booking_created_at,
  updated_at                                                 AS booking_updated_at
FROM dedup
WHERE rn = 1
  AND total_amount IS NOT NULL
  AND total_amount >= 0
  AND check_in IS NOT NULL
  AND check_out > check_in;

-- ---------------------------------------------------------------------
-- 2. dim_property: property and destination (pre-joined, no free text)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_property
COMMENT 'Property attributes with destination, country and region.'
AS
SELECT
  p.property_id,
  p.host_id,
  p.title                                   AS property_title,
  INITCAP(TRIM(p.property_type))            AS property_type,
  CAST(p.base_price AS DECIMAL(18,2))       AS base_price,
  p.max_guests,
  p.bedrooms,
  p.bathrooms,
  p.destination_id,
  d.destination,
  d.country                                 AS destination_country,
  d.state_or_province                       AS destination_region,
  d.state_or_province_code                  AS destination_region_code,
  CAST(p.created_at AS DATE)                AS listed_date
FROM samples.wanderbricks.properties p
LEFT JOIN samples.wanderbricks.destinations d
  ON p.destination_id = d.destination_id;

-- ---------------------------------------------------------------------
-- 3. dim_guest: PII-free guest attributes (email and name removed)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_guest
COMMENT 'Guest (user) attributes. PII (email, name) intentionally excluded.'
AS
SELECT
  user_id,
  country                                   AS guest_country,
  LOWER(TRIM(user_type))                    AS guest_type,
  COALESCE(is_business, FALSE)              AS is_business,
  CASE WHEN is_business THEN company_name END AS company_name,
  CAST(created_at AS DATE)                  AS signup_date
FROM samples.wanderbricks.users;

-- ---------------------------------------------------------------------
-- 4. dim_host: PII-free host attributes (name, email, phone removed)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_host
COMMENT 'Host attributes. PII (name, email, phone) intentionally excluded; identify hosts by host_id.'
AS
SELECT
  host_id,
  CONCAT('Host-', CAST(host_id AS STRING))  AS host_label,
  country                                   AS host_country,
  rating                                    AS host_rating,
  is_verified,
  is_active,
  joined_at                                 AS host_joined_date
FROM samples.wanderbricks.hosts;

-- ---------------------------------------------------------------------
-- 5. v_booking_revenue: one wide view for Genie (fact plus all dimensions)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_booking_revenue
COMMENT 'Wide, Genie-friendly view: one row per booking with property, destination, guest and host attributes.'
AS
SELECT
  f.*,
  p.property_title, p.property_type, p.base_price, p.bedrooms, p.max_guests,
  p.destination_id, p.destination, p.destination_country, p.destination_region,
  g.guest_country, g.guest_type, g.is_business, g.company_name,
  h.host_id, h.host_label, h.host_country, h.host_rating, h.is_verified AS host_is_verified,
  h.is_active AS host_is_active
FROM fact_bookings f
LEFT JOIN dim_property p ON f.property_id = p.property_id
LEFT JOIN dim_guest    g ON f.user_id     = g.user_id
LEFT JOIN dim_host     h ON p.host_id     = h.host_id;

-- ---------------------------------------------------------------------
-- Column comments (Genie reads these)
-- ---------------------------------------------------------------------
COMMENT ON COLUMN fact_bookings.confirmed_revenue IS 'Booking amount if status = confirmed, else 0. SUM this for revenue.';
COMMENT ON COLUMN fact_bookings.booking_date      IS 'Date the booking was made (from created_at). Use for "bookings made in ..." questions.';
COMMENT ON COLUMN fact_bookings.stay_start_date   IS 'Check-in date. Use for "stays in ..." and revenue-by-period questions.';
COMMENT ON COLUMN fact_bookings.nights            IS 'Length of stay in nights = datediff(check_out, check_in).';
COMMENT ON COLUMN fact_bookings.status            IS 'Booking status, lower-case (e.g. confirmed, pending, cancelled).';
