-- =====================================================================
-- OPTIONAL: load the synthetic CSVs (data/csv/*.csv) into Unity Catalog
-- Use this if your workspace has no samples.wanderbricks, or if you want
-- the dataset with deliberately dirty rows to demo the cleanup.
--
-- Steps:
--   1. Run the CREATE statements below.
--   2. Catalog → wanderbricks_genie → bronze → raw_files → "Upload to this volume"
--      and upload the 5 CSV files from data/csv/.
--   3. Run the CREATE TABLE ... AS statements.
--   4. In sql/01_gold_views.sql, find/replace
--        samples.wanderbricks   →   wanderbricks_genie.bronze
-- =====================================================================

CREATE CATALOG IF NOT EXISTS wanderbricks_genie;
CREATE SCHEMA  IF NOT EXISTS wanderbricks_genie.bronze COMMENT 'Raw synthetic Wanderbricks data';
CREATE VOLUME  IF NOT EXISTS wanderbricks_genie.bronze.raw_files;

CREATE OR REPLACE TABLE wanderbricks_genie.bronze.destinations AS
SELECT * FROM read_files('/Volumes/wanderbricks_genie/bronze/raw_files/destinations.csv',
  format => 'csv', header => true, inferSchema => true, multiLine => true);

CREATE OR REPLACE TABLE wanderbricks_genie.bronze.hosts AS
SELECT * FROM read_files('/Volumes/wanderbricks_genie/bronze/raw_files/hosts.csv',
  format => 'csv', header => true, inferSchema => true);

CREATE OR REPLACE TABLE wanderbricks_genie.bronze.properties AS
SELECT * FROM read_files('/Volumes/wanderbricks_genie/bronze/raw_files/properties.csv',
  format => 'csv', header => true, inferSchema => true);

CREATE OR REPLACE TABLE wanderbricks_genie.bronze.users AS
SELECT * FROM read_files('/Volumes/wanderbricks_genie/bronze/raw_files/users.csv',
  format => 'csv', header => true, inferSchema => true);

CREATE OR REPLACE TABLE wanderbricks_genie.bronze.bookings AS
SELECT * FROM read_files('/Volumes/wanderbricks_genie/bronze/raw_files/bookings.csv',
  format => 'csv', header => true, inferSchema => true);

-- Quick check: expect 30 / 200 / 600 / 2000 / 10075 rows
SELECT 'destinations' t, COUNT(*) FROM wanderbricks_genie.bronze.destinations UNION ALL
SELECT 'hosts', COUNT(*) FROM wanderbricks_genie.bronze.hosts UNION ALL
SELECT 'properties', COUNT(*) FROM wanderbricks_genie.bronze.properties UNION ALL
SELECT 'users', COUNT(*) FROM wanderbricks_genie.bronze.users UNION ALL
SELECT 'bookings', COUNT(*) FROM wanderbricks_genie.bronze.bookings;
