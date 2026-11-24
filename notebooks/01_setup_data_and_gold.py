# Databricks notebook source
# MAGIC %md
# MAGIC # Setup: load data + build Gold views
# MAGIC
# MAGIC **What this notebook does (one click: "Run all"):**
# MAGIC 1. Reads the 5 CSV files from this Git folder (`data/csv/`). No manual upload needed.
# MAGIC 2. Saves them as **bronze** tables in Unity Catalog.
# MAGIC 3. Runs `sql/01_gold_views.sql` to build the clean **gold** views.
# MAGIC 4. Runs quick checks and prints the benchmark answers.
# MAGIC
# MAGIC **Before running:** at the top, attach the notebook to **Serverless** compute.
# MAGIC If you get a "permission to create catalog" error, set the `catalog` box above to `workspace` and run again.

# COMMAND ----------

dbutils.widgets.text("catalog", "wanderbricks_genie", "Catalog to use")
CATALOG = dbutils.widgets.get("catalog").strip()

from pathlib import Path

# The notebook runs from <repo>/notebooks, so the repo root is one folder up
REPO = Path.cwd().parent
CSV_DIR = REPO / "data" / "csv"
SQL_FILE = REPO / "sql" / "01_gold_views.sql"
assert CSV_DIR.exists(), f"Cannot find {CSV_DIR}. Open this notebook from inside the Git folder."
print("Repo folder :", REPO)
print("Catalog     :", CATALOG)

# COMMAND ----------

# MAGIC %md ## 1. Create catalog and schemas

# COMMAND ----------

try:
    spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
except Exception as e:
    print(f"Could not create catalog '{CATALOG}' (it may already exist, or you lack permission):\n  {str(e)[:200]}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.bronze COMMENT 'Raw synthetic Wanderbricks data'")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.gold COMMENT 'Curated Gold views for the Revenue & Booking Analyst Genie agent'")
print("Schemas ready:", f"{CATALOG}.bronze", f"{CATALOG}.gold")

# COMMAND ----------

# MAGIC %md ## 2. Load the 5 CSVs into bronze tables

# COMMAND ----------

import pandas as pd
from pyspark.sql import functions as F

DATE_COLS = {"check_in", "check_out", "joined_at"}
TS_COLS = {"created_at", "updated_at"}
DECIMAL_COLS = {"total_amount", "base_price"}

def load(table: str):
    pdf = pd.read_csv(CSV_DIR / f"{table}.csv", keep_default_na=True)
    for c in pdf.columns:
        if c in DATE_COLS:
            pdf[c] = pd.to_datetime(pdf[c]).dt.date
        elif c in TS_COLS:
            pdf[c] = pd.to_datetime(pdf[c])
        elif pdf[c].dtype == object:
            pdf[c] = pdf[c].where(pdf[c].notna(), None)      # empty text -> NULL
    sdf = spark.createDataFrame(pdf.astype(object).where(pdf.notna(), None))
    for c in DECIMAL_COLS & set(pdf.columns):
        sdf = sdf.withColumn(c, F.col(c).cast("decimal(18,2)"))
    sdf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(f"{CATALOG}.bronze.{table}")
    print(f"  {CATALOG}.bronze.{table:<13} {sdf.count():>6} rows")

for t in ["destinations", "hosts", "properties", "users", "bookings"]:
    load(t)

# COMMAND ----------

# MAGIC %md ## 3. Build the gold views (runs `sql/01_gold_views.sql`)

# COMMAND ----------

sql_text = SQL_FILE.read_text()
sql_text = sql_text.replace("samples.wanderbricks", f"{CATALOG}.bronze")
sql_text = sql_text.replace("wanderbricks_genie", CATALOG)
lines = [l for l in sql_text.splitlines() if not l.strip().startswith("--")]
statements = [s.strip() for s in "\n".join(lines).split(";") if s.strip()]

for stmt in statements:
    first_line = stmt.splitlines()[0][:80]
    try:
        spark.sql(stmt)
        print("OK   ", first_line)
    except Exception as e:
        if first_line.upper().startswith("CREATE CATALOG"):
            print("SKIP ", first_line, "(catalog already handled in step 1)")
        elif first_line.upper().startswith("COMMENT ON"):
            print("SKIP ", first_line, "(column comments not supported here; safe to ignore)")
        else:
            raise

# COMMAND ----------

# MAGIC %md ## 4. Checks (expect: 9925 gold rows, 0 duplicates, 0 bad nights, 3 status values)

# COMMAND ----------

display(spark.sql(f"""
SELECT (SELECT COUNT(*) FROM {CATALOG}.bronze.bookings)          AS bronze_rows,
       (SELECT COUNT(*) FROM {CATALOG}.gold.fact_bookings)       AS gold_rows,
       (SELECT COUNT(*) FROM {CATALOG}.gold.v_booking_revenue)   AS wide_view_rows,
       (SELECT COUNT(*) - COUNT(DISTINCT booking_id) FROM {CATALOG}.gold.fact_bookings) AS duplicates,
       (SELECT COUNT(*) FROM {CATALOG}.gold.fact_bookings WHERE nights <= 0)            AS bad_nights
"""))
display(spark.sql(f"SELECT status, COUNT(*) AS bookings FROM {CATALOG}.gold.fact_bookings GROUP BY status ORDER BY bookings DESC"))

# COMMAND ----------

# MAGIC %md ## 5. Benchmark answers (compare with what Genie says later)

# COMMAND ----------

V = f"{CATALOG}.gold.v_booking_revenue"
display(spark.sql(f"""
SELECT 'Q1 revenue last quarter' AS question, CAST(ROUND(SUM(confirmed_revenue),2) AS STRING) AS answer FROM {V}
 WHERE stay_start_date >= add_months(date_trunc('quarter', current_date()), -3)
   AND stay_start_date <  date_trunc('quarter', current_date())
UNION ALL
SELECT 'Q5 business share % (confirmed)',
       CAST(ROUND(100.0 * SUM(CASE WHEN is_business THEN 1 ELSE 0 END) / COUNT(*), 1) AS STRING) FROM {V} WHERE is_confirmed
"""))
display(spark.sql(f"SELECT destination, destination_country, COUNT(*) AS confirmed_bookings FROM {V} WHERE is_confirmed GROUP BY 1,2 ORDER BY 3 DESC LIMIT 10"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Done
# MAGIC Next: create the Genie space on the 5 views in **`<catalog>.gold`**. See `SETUP_GUIDE.md`, step 4.
