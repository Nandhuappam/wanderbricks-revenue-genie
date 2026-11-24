# Step-by-Step Setup Guide (Beginner Friendly)

This guide takes you from the GitHub repo to a working **Genie AI agent** and **Databricks App**.
It takes about 30 minutes. You only click in the Databricks website; no local installs are needed.

```
GitHub repo ──(Step 2: Git folder)──▶ Databricks workspace
                                        │
             Step 3: run notebook ──────┤──▶ bronze tables (raw CSV data)
                                        │──▶ gold views  (clean, no PII)
             Step 4: Genie space ───────┤──▶ AI agent that answers questions
             Step 5: Databricks App ────┘──▶ chat web page for business users
```

---

## Step 1: Connect GitHub to Databricks (one time)

> The repo is **public**, so you can skip this step and go straight to Step 2 if you only need to *read* it.
> Do this step if you want to **commit/push changes from Databricks back to GitHub**.

1. On GitHub, open **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic)**.
2. Name it `databricks`, choose an expiry date, and tick the **`repo`** scope. Click **Generate token** and **copy** it.
3. In Databricks, click your **profile icon (top right) → Settings → Linked accounts** (some workspaces call it *Git integration*).
4. Click **Add Git credential**:
   - Git provider: **GitHub**
   - Git provider username: `Nandhuappam`
   - Token: paste the token
5. Click **Save**.

## Step 2: Bring the repo into Databricks (Git folder)

1. In the left sidebar, click **Workspace**.
2. Open your user folder (**Workspace → Users → your email**).
3. Click **Create** (top right) **→ Git folder**.
4. Fill in:
   - Git repository URL: `https://github.com/Nandhuappam/wanderbricks-revenue-genie`
   - Git provider: **GitHub** (filled in automatically)
   - Git folder name: `wanderbricks-revenue-genie`
5. Click **Create Git folder**.

You will now see all the repo files (`data/`, `sql/`, `genie/`, `app/`, `notebooks/` …) inside Databricks.
To fetch new changes from GitHub later: open the folder, click the **branch name (`main`) → Pull**.

## Step 3: Load the data and build the Gold views (one notebook)

1. In the Git folder, open **`notebooks/01_setup_data_and_gold`**.
2. At the top right, click **Connect** and choose **Serverless**.
3. Click **Run all**.
4. Wait about 1–2 minutes. At the end you should see:
   - `gold_rows = 9925`, `duplicates = 0`, `bad_nights = 0`
   - 3 status values: `confirmed`, `cancelled`, `pending`

**If you see "permission denied to create catalog":** change the **catalog** box at the top of the notebook from `wanderbricks_genie` to **`workspace`** and click **Run all** again.
(Databricks Free Edition always has a catalog called `workspace`.) Use that catalog name in the next steps.

**Check it worked:** in the sidebar, open **Catalog → wanderbricks_genie** (or `workspace`) **→ gold**. You should see 5 views:
`fact_bookings`, `dim_property`, `dim_guest`, `dim_host`, `v_booking_revenue`.

> This notebook does what the old "upload 5 CSVs + run 00 + run 01" instructions did, automatically.
> It reads the CSVs straight from the Git folder, so nothing needs uploading.

## Step 4: Create the Genie space (the AI agent)

1. In the sidebar, click **Genie → New** (top right).
2. **Choose data sources:** open your catalog → **gold**, tick all **5 views**, and click **Create**.
3. Click **Settings** (gear icon) in the Genie space:
   - **Title:** `Revenue & Booking Analyst`
   - **Description:** `Ask plain-English questions about bookings, revenue, destinations, properties, guests and hosts.`
   - **Default warehouse:** pick the Serverless Starter Warehouse, then click **Save**.
4. Click **Instructions → General instructions**.
   Open `genie/instructions.md` in your Git folder, copy **everything inside the grey `text` box** (from *"You are the Revenue & Booking Analyst…"* to the end of *STYLE*), paste it, and click **Save**.
5. Click **Instructions → SQL queries → Add**. For each of **Q1–Q5** in `genie/benchmark_questions.md`:
   - Question: the question text, e.g. `What was total booking revenue last quarter?`
   - SQL: the SQL under it. **If you used the `workspace` catalog**, replace `wanderbricks_genie` with `workspace` in the SQL.
   - Click **Save**.
6. **Test:** in the chat box, type `What share of bookings come from business users?` and expect about **18.4%**.
7. **Benchmarks** (optional but recommended): click **Benchmarks → Add benchmark** for all 10 questions, using the SQL as the "ground truth", then **Run all**. Target ≥ 9/10.
8. **Copy the space ID:** look at the browser URL, `…/genie/rooms/`**`01f0abc123…`**`?o=…`. The long code after `rooms/` is the **Genie space ID**.

## Step 5: Create the Databricks App and link it to Genie

1. In the sidebar, click **Compute → Apps tab → Create app**.
2. Choose **Create a custom app**, name it `revenue-booking-analyst`, and click **Next: Configure**.
3. Under **App resources**, click **+ Add resource → Genie space**:
   - Select your **Revenue & Booking Analyst** space
   - Permission: **Can run**
   - Resource key: **`genie-space`** (must be exactly this; `app.yaml` reads it)
4. Click **Create app** and wait until the compute status shows **Active** (2–3 minutes).
5. Click **Deploy**, browse to your Git folder, select the **`app`** folder (`…/wanderbricks-revenue-genie/app`), and click **Deploy**.
6. Give the app permission to read the data. Open the app's **Authorization** tab and copy the **service principal** name, then in a SQL editor run (use your catalog name):
   ```sql
   GRANT USE CATALOG ON CATALOG wanderbricks_genie TO `<service-principal-name>`;
   GRANT USE SCHEMA  ON SCHEMA  wanderbricks_genie.gold TO `<service-principal-name>`;
   GRANT SELECT      ON SCHEMA  wanderbricks_genie.gold TO `<service-principal-name>`;
   ```
   Also open **SQL Warehouses → your warehouse → Permissions**, add the service principal, and give it **Can use**.
7. When the status shows **Running**, click the app **URL**. You'll see the chat page; click a sample question in the left sidebar.

## Step 6: Share it

- Genie space: **Share** (top right), then add your Pod Lead with **Can run**.
- App: **Permissions**, then add users with **Can use**.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Notebook: `Cannot find .../data/csv` | Open the notebook from **inside the Git folder**, not a copy |
| Notebook: permission to create catalog | Set the catalog box to `workspace` and run again |
| Genie gives a different revenue number | Check the instructions were saved; check the SQL uses `confirmed_revenue` |
| App says `GENIE_SPACE_ID is not set` | The resource key must be exactly `genie-space`; redeploy |
| App shows an error when answering | Run the GRANTs in Step 5.6 and give the service principal **Can use** on the warehouse |
| New changes on GitHub not showing | In the Git folder, click **main → Pull** |
