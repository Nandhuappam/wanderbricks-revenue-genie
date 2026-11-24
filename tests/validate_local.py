"""Local check of the Gold cleanup rules and benchmark answers on the synthetic CSVs (DuckDB).

Mirrors sql/01_gold_views.sql in DuckDB syntax. Run: pip install duckdb && python tests/validate_local.py
"""
from pathlib import Path
import duckdb

CSV = Path(__file__).resolve().parent.parent / "data" / "csv"
con = duckdb.connect()
for t in ["bookings", "properties", "destinations", "users", "hosts"]:
    con.execute(f"CREATE VIEW src_{t} AS SELECT * FROM read_csv_auto('{CSV / (t + '.csv')}', header=true)")

con.execute("""
CREATE VIEW fact_bookings AS
WITH d AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY booking_id ORDER BY updated_at DESC) rn FROM src_bookings)
SELECT booking_id, user_id, property_id, check_in AS stay_start_date, check_out AS stay_end_date,
       datediff('day', check_in, check_out) AS nights, guests_count,
       CAST(total_amount AS DECIMAL(18,2)) AS total_amount, lower(trim(status)) AS status,
       lower(trim(status)) = 'confirmed' AS is_confirmed,
       CASE WHEN lower(trim(status)) = 'confirmed' THEN CAST(total_amount AS DECIMAL(18,2)) ELSE 0 END AS confirmed_revenue,
       CAST(created_at AS DATE) AS booking_date
FROM d WHERE rn = 1 AND total_amount IS NOT NULL AND total_amount >= 0 AND check_in IS NOT NULL AND check_out > check_in""")
con.execute("""
CREATE VIEW v AS SELECT f.*, upper(substr(trim(p.property_type),1,1)) || substr(trim(p.property_type),2) AS property_type, d.destination, d.country AS destination_country,
       u.is_business, h.host_id, 'Host-' || h.host_id AS host_label, h.rating AS host_rating, h.is_verified AS host_is_verified
FROM fact_bookings f LEFT JOIN src_properties p USING (property_id)
LEFT JOIN src_destinations d ON p.destination_id = d.destination_id
LEFT JOIN src_users u ON f.user_id = u.user_id LEFT JOIN src_hosts h ON p.host_id = h.host_id""")

TODAY = "DATE '2026-11-24'"
checks = {
    "Source rows / Gold rows": "SELECT (SELECT COUNT(*) FROM src_bookings), (SELECT COUNT(*) FROM fact_bookings)",
    "Raw status values": "SELECT status, COUNT(*) FROM src_bookings GROUP BY 1 ORDER BY 2 DESC",
    "Gold status values": "SELECT status, COUNT(*) FROM fact_bookings GROUP BY 1 ORDER BY 2 DESC",
    "Gold dup ids / bad nights": "SELECT COUNT(*) - COUNT(DISTINCT booking_id), SUM(CASE WHEN nights<=0 THEN 1 ELSE 0 END) FROM fact_bookings",
    "Wide view fan-out check (fact vs wide)": "SELECT (SELECT COUNT(*) FROM fact_bookings), (SELECT COUNT(*) FROM v)",
    "Q1 revenue last quarter (Q3 2026)": f"""SELECT ROUND(SUM(confirmed_revenue),2) FROM v
        WHERE stay_start_date >= date_trunc('quarter', {TODAY}) - INTERVAL 3 MONTH AND stay_start_date < date_trunc('quarter', {TODAY})""",
    "Q2 top 5 destinations (confirmed bookings)": "SELECT destination, destination_country, COUNT(*) c FROM v WHERE is_confirmed GROUP BY 1,2 ORDER BY c DESC LIMIT 5",
    "Q3 avg booking value by property type": "SELECT property_type, ROUND(SUM(confirmed_revenue)/COUNT(*),2) a FROM v WHERE is_confirmed GROUP BY 1 ORDER BY a DESC",
    "Q4 top 5 hosts by revenue": "SELECT host_label, host_rating, ROUND(SUM(confirmed_revenue),2) r FROM v WHERE is_confirmed GROUP BY 1,2 ORDER BY r DESC LIMIT 5",
    "Q5 business share % (confirmed)": "SELECT ROUND(100.0*SUM(CASE WHEN is_business THEN 1 ELSE 0 END)/COUNT(*),1) FROM v WHERE is_confirmed",
    "Q7 cancellation rate % (top 3 countries)": "SELECT destination_country, ROUND(100.0*SUM(CASE WHEN status='cancelled' THEN 1 ELSE 0 END)/COUNT(*),1) r FROM v GROUP BY 1 ORDER BY r DESC LIMIT 3",
    "Q8 avg nights by property type": "SELECT property_type, ROUND(AVG(nights),1) FROM v WHERE is_confirmed GROUP BY 1 ORDER BY 2 DESC",
    "Q10 pending bookings / amount": "SELECT COUNT(*), ROUND(SUM(total_amount),2) FROM v WHERE status='pending'",
}
for name, sql in checks.items():
    print(f"\n== {name}")
    for row in con.execute(sql).fetchall():
        print("  ", row)

dup, bad = con.execute("SELECT COUNT(*) - COUNT(DISTINCT booking_id), SUM(CASE WHEN nights<=0 THEN 1 ELSE 0 END) FROM fact_bookings").fetchone()
fact, wide = con.execute("SELECT (SELECT COUNT(*) FROM fact_bookings), (SELECT COUNT(*) FROM v)").fetchone()
assert dup == 0 and bad == 0 and fact == wide, "Gold validation failed"
print("\nALL GOLD CHECKS PASSED")
