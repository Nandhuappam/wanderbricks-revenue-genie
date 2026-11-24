# Revenue & Booking Analyst: Genie Agent + Databricks App on `samples.wanderbricks`

> **Status:** Proposed. Submitted Nov 24 for Pod Lead review and validation.
> **Owner:** Data & Analytics Team
> **Data source:** `samples.wanderbricks` (built-in Unity Catalog sample: a simulated travel-booking platform)
> **Full use-case document:** [`docs/Genie_Use_Case_Revenue_Booking_Analyst.pdf`](docs/Genie_Use_Case_Revenue_Booking_Analyst.pdf)

---

## 5-Point Game Plan

### 1. The Problem & User

| | |
|---|---|
| **Who** | Revenue analysts, market/destination managers, and business leaders. They know the business but don't write SQL. |
| **Daily headache** | Every revenue or booking question ("What was revenue last quarter?", "Which destinations are growing?") turns into a ticket to the data team. Each answer takes **hours to days**, and different people calculate "revenue" differently (some include pending or cancelled bookings, some don't). |
| **What we're building** | A **Genie AI Agent** that answers these questions in plain English using governed Gold views, wrapped in a **Databricks App** so business users get a simple chat page with answers, tables and the SQL behind each answer. |

### 2. The Data (5 tables + cleanup)

Source: existing Unity Catalog tables in `samples.wanderbricks` (no synthetic data needed).

| # | Source table | Role | Key columns | Cleanup needed |
|---|---|---|---|---|
| 1 | `bookings` | **Fact** | booking_id, user_id, property_id, check_in, check_out, guests_count, total_amount, status, created_at | Standardise `status` (trim/lower-case); drop rows where `check_out <= check_in` or `total_amount` is null/negative; dedupe on `booking_id` (keep latest `updated_at`) |
| 2 | `properties` | Dimension | property_id, host_id, destination_id, property_type, base_price, bedrooms, max_guests | Standardise `property_type` casing; drop free-text `description` from the agent |
| 3 | `destinations` | Dimension | destination_id, destination, country, state_or_province | Drop the long markdown `description` column (it only adds noise for the agent) |
| 4 | `users` | Dimension | user_id, country, user_type, is_business | **PII:** exclude `email` and `name` |
| 5 | `hosts` | Dimension | host_id, rating, is_verified, is_active, country | **PII:** exclude `email` and `phone`; mask `name` (show `host_id` instead) |

**Join model (star schema):** `bookings → properties → destinations`, `bookings → users`, `properties → hosts`.
`bookings` has no destination key, so destination is always reached **through properties**.

Cleaned data is published as Gold views in **`wanderbricks_genie.gold`** (see [`sql/01_gold_views.sql`](sql/01_gold_views.sql)):

| Gold view | Purpose |
|---|---|
| `gold.fact_bookings` | Clean bookings plus derived `nights`, `booking_date`, `is_confirmed`, `confirmed_revenue` |
| `gold.dim_property` | Property attributes plus destination (pre-joined) |
| `gold.dim_guest` | PII-free guest attributes |
| `gold.dim_host` | PII-free host attributes |
| `gold.v_booking_revenue` | One wide, Genie-friendly view (fact plus all dimensions) |

Optional roadmap tables: `payments`, `reviews`, `amenities` / `property_amenities`.

### 3. Sample Questions (what users will type)

1. *"What was total booking revenue last quarter?"*
2. *"Which destinations had the most confirmed bookings?"*
3. *"What's the average booking value by property type?"*
4. *"Who are the top 10 hosts by total revenue?"*
5. *"What share of bookings come from business users?"*

The expected SQL for each question, plus 5 harder ones, is in [`genie/benchmark_questions.md`](genie/benchmark_questions.md).

### 4. Build Plan

| Step | What we do | Deliverable in this repo |
|---|---|---|
| **1. Bronze → Gold** | Read `samples.wanderbricks`, apply the cleanup rules above, remove PII, add derived columns | [`sql/01_gold_views.sql`](sql/01_gold_views.sql) |
| **2. Data-quality checks** | Row counts, status values, null/negative amounts, bad date ranges, orphan keys | [`sql/02_data_quality_checks.sql`](sql/02_data_quality_checks.sql) |
| **3. Genie Agent** | Create a Genie space on the Gold views; add business rules, column descriptions and example SQL | [`genie/instructions.md`](genie/instructions.md) |
| **4. Benchmark & accuracy** | Load 10 benchmark Q&A pairs into Genie *Benchmarks*; target ≥ 90% correct before sharing | [`genie/benchmark_questions.md`](genie/benchmark_questions.md) |
| **5. Databricks App** | A Streamlit chat app that calls the Genie Conversation API and shows the answer, a result table and the SQL | [`app/`](app/) |
| **6. Pilot** | Pod Lead sign-off, then 5–10 pilot users; track adoption and accuracy | — |

**Business rules given to the agent (summary):**
- **Revenue** = `SUM(total_amount)` where `status = 'confirmed'` **only**.
- **Booking date** = `created_at`; **stay date** = `check_in` (use for "stays in March" style questions).
- **Average Booking Value** = confirmed revenue ÷ confirmed bookings.
- **Length of stay** = `datediff(check_out, check_in)`.
- "Last quarter" means the previous full calendar quarter.
- Never return guest or host personal details.

### 5. The Business Impact

| Benefit | Target |
|---|---|
| **Time saved** | ≥ 10 analyst hours/week freed from ad-hoc revenue requests |
| **Speed** | Answers in **seconds** instead of hours or days |
| **Consistency** | One governed definition of revenue (confirmed only), so every team gets the same number |
| **Trust** | Every answer shows the SQL; Gold views carry no PII |
| **Adoption** | ≥ 50% of target users asking ≥ 1 question/week by week 4 |

---

## Repository layout

```
├── README.md                        ← 5-point game plan (this file)
├── docs/
│   └── Genie_Use_Case_Revenue_Booking_Analyst.pdf
├── sql/
│   ├── 01_gold_views.sql            ← cleanup + Gold views (PII removed)
│   └── 02_data_quality_checks.sql   ← checks to run before and after
├── genie/
│   ├── instructions.md              ← paste into Genie "General instructions"
│   └── benchmark_questions.md       ← 10 benchmark questions + expected SQL
└── app/
    ├── app.py                       ← Streamlit chat UI over the Genie API
    ├── app.yaml                     ← Databricks App config
    └── requirements.txt
```

## Quick start

1. **Gold layer:** in a SQL warehouse, run `sql/02_data_quality_checks.sql` (section A), then `sql/01_gold_views.sql`.
   Change the catalog name `wanderbricks_genie` if your team uses a different one.
2. **Genie space:** *New → Genie space*, add the 5 `wanderbricks_genie.gold.*` views, paste `genie/instructions.md` into the instructions, and add the example SQL from `genie/benchmark_questions.md`.
3. **Benchmark:** add the 10 questions under *Benchmarks*, run them, and fix the instructions until accuracy is ≥ 90%.
4. **App:** *Compute → Apps → Create app → Custom*, point it at the `app/` folder, add the Genie space as an app resource with key `genie-space` (*Can run*), and deploy.
   Give the app's service principal `SELECT` on the Gold views and *Can use* on the SQL warehouse.
