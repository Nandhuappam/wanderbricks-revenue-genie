# Benchmark Questions: Revenue & Booking Analyst

Load these into **Genie → Benchmarks**. Questions Q1–Q5 are the core user prompts and should also be added as *example SQL* (trusted assets).
Q6–Q10 are held out to test how well the agent generalises.
**Target: ≥ 9 / 10 correct** before Pod Lead sign-off.

All queries use `wanderbricks_genie.gold`.

---

## Core prompts (from the use-case document)

### Q1. "What was total booking revenue last quarter?"
```sql
SELECT ROUND(SUM(confirmed_revenue), 2) AS revenue
FROM wanderbricks_genie.gold.v_booking_revenue
WHERE stay_start_date >= add_months(date_trunc('quarter', current_date()), -3)
  AND stay_start_date <  date_trunc('quarter', current_date());
```

### Q2. "Which destinations had the most confirmed bookings?"
```sql
SELECT destination, destination_country, COUNT(*) AS confirmed_bookings
FROM wanderbricks_genie.gold.v_booking_revenue
WHERE is_confirmed
GROUP BY destination, destination_country
ORDER BY confirmed_bookings DESC
LIMIT 10;
```

### Q3. "What's the average booking value by property type?"
```sql
SELECT property_type,
       ROUND(SUM(confirmed_revenue) / COUNT(*), 2) AS avg_booking_value
FROM wanderbricks_genie.gold.v_booking_revenue
WHERE is_confirmed
GROUP BY property_type
ORDER BY avg_booking_value DESC;
```

### Q4. "Who are the top 10 hosts by total revenue?"
```sql
SELECT host_id, host_label, host_rating,
       ROUND(SUM(confirmed_revenue), 2) AS total_revenue
FROM wanderbricks_genie.gold.v_booking_revenue
WHERE is_confirmed
GROUP BY host_id, host_label, host_rating
ORDER BY total_revenue DESC
LIMIT 10;
```

### Q5. "What share of bookings come from business users?"
```sql
SELECT ROUND(100.0 * SUM(CASE WHEN is_business THEN 1 ELSE 0 END) / COUNT(*), 1) AS business_share_pct
FROM wanderbricks_genie.gold.v_booking_revenue
WHERE is_confirmed;
```

---

## Held-out benchmark questions

### Q6. "What is the monthly revenue trend for this year?"
```sql
SELECT date_trunc('month', stay_start_date) AS month,
       ROUND(SUM(confirmed_revenue), 2)     AS revenue
FROM wanderbricks_genie.gold.v_booking_revenue
WHERE year(stay_start_date) = year(current_date())
GROUP BY 1 ORDER BY 1;
```

### Q7. "What is the cancellation rate by destination country?"
```sql
SELECT destination_country,
       ROUND(100.0 * SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) / COUNT(*), 1) AS cancellation_rate_pct
FROM wanderbricks_genie.gold.v_booking_revenue
GROUP BY destination_country
ORDER BY cancellation_rate_pct DESC;
```

### Q8. "What's the average length of stay by property type?"
```sql
SELECT property_type, ROUND(AVG(nights), 1) AS avg_nights
FROM wanderbricks_genie.gold.v_booking_revenue
WHERE is_confirmed
GROUP BY property_type
ORDER BY avg_nights DESC;
```

### Q9. "Do verified hosts earn more revenue per booking than unverified hosts?"
```sql
SELECT host_is_verified,
       COUNT(*)                                    AS confirmed_bookings,
       ROUND(SUM(confirmed_revenue) / COUNT(*), 2) AS avg_booking_value
FROM wanderbricks_genie.gold.v_booking_revenue
WHERE is_confirmed
GROUP BY host_is_verified;
```

### Q10. "How many bookings are still pending, and what amount do they represent?"
```sql
SELECT COUNT(*) AS pending_bookings, ROUND(SUM(total_amount), 2) AS pending_amount
FROM wanderbricks_genie.gold.v_booking_revenue
WHERE status = 'pending';
```

---

## Expected answers on the synthetic dataset

These come from `tests/validate_local.py`, with "today" set to 2026-11-24 so that last quarter is Q3 2026.

| # | Expected result |
|---|---|
| Q1 | Revenue last quarter = **879,572.47** |
| Q2 | Vancouver 298, New York 296, Amsterdam 294, London 288, Berlin 279 |
| Q3 | Villa 2,373.47 · House 1,049.59 · Loft 971.70 · Cabin 824.42 · Condo 717.01 · Apartment 632.15 · Studio 471.01 |
| Q4 | Host-160 117,458.66 · Host-2 107,273.92 · Host-138 106,389.51 · … |
| Q5 | **18.4%** of confirmed bookings are from business users |
| Q7 | France 20.3% · UAE 20.0% · Italy 19.4% (highest) |
| Q10 | **1,262** pending bookings worth **1,092,225.09** |

---

## Scoring sheet

| # | Question | Correct SQL? | Correct number? | Notes |
|---|---|---|---|---|
| Q1 | Revenue last quarter | ☐ | ☐ | |
| Q2 | Top destinations | ☐ | ☐ | |
| Q3 | ABV by property type | ☐ | ☐ | |
| Q4 | Top 10 hosts | ☐ | ☐ | |
| Q5 | Business share | ☐ | ☐ | |
| Q6 | Monthly trend | ☐ | ☐ | |
| Q7 | Cancellation rate | ☐ | ☐ | |
| Q8 | Avg length of stay | ☐ | ☐ | |
| Q9 | Verified vs unverified | ☐ | ☐ | |
| Q10 | Pending pipeline | ☐ | ☐ | |
