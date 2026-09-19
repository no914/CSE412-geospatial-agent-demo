# CSE 412 Geospatial LLM-Agent Mini Template

A **small teaching reference** for the CSE 412 group project scenario:
**Integrating and querying satellite and geospatial data**.

This repository is intentionally **not a complete project solution**. It demonstrates the same core pattern as the course hotel-agent reference:

```text
natural-language question
        ↓
     LLM agent
        ↓
choose a deterministic tool
        ↓
PostgreSQL / metadata
        ↓
rows + evidence
        ↓
answer grounded in returned data
```

The example uses the **Fields of The World (FTW)** dataset conceptually together with a simplified national agricultural-statistics table. Instead of loading billions of field polygons into PostgreSQL, the starter stores **country/year summaries** so students can focus on database design, SQL, data integration, and agent tools first.

## What this template demonstrates

- PostgreSQL as the primary database.
- Integration of two heterogeneous sources by `country_code + year`.
- A metadata table describing the origin and meaning of each source.
- Four agent-accessible tools:
  1. `get_database_schema()`
  2. `search_metadata(query)`
  3. `execute_sql(sql)`
  4. `compare_country_year(country_code, year)`
- Read-only SQL safety checks.
- A minimal Gemini function-calling loop.
- Evidence-first output: SQL/tool results are shown before the final answer.

## Dataset idea

Primary source:
- Fields of The World (FTW) global map: https://source.coop/ftw/global-data

Possible related source:
- FAOSTAT agricultural / land-use statistics.

The FTW global collection provides country-partitioned field-boundary GeoParquet files. Relevant attributes include field `confidence`, `metrics:area`, and `determination:datetime` (year). This template aggregates those rows into a much smaller table before loading them into PostgreSQL.

> **Important:** FTW field area and national cropland statistics are not necessarily measuring exactly the same concept. Treat the comparison in this demo as a database/data-integration example, not as a scientific validation result.

## Repository structure

```text
.
├── .env.example
├── .gitignore
├── requirements.txt
├── db.py
├── tools.py
├── agent.py
├── main.py
├── sql/
│   ├── schema.sql
│   └── demo_data.sql
└── scripts/
    └── load_ftw_summary.py
```

## 1. Create the database

Create a PostgreSQL database, then run:

```bash
psql -d geospatial_demo -f sql/schema.sql
psql -d geospatial_demo -f sql/demo_data.sql
```

`demo_data.sql` contains **illustrative placeholder values only** so the code can be exercised immediately. Students should replace them with real data for their own project.

## 2. Create a read-only agent account

Run as a database owner/admin:

```sql
CREATE USER agent_ro WITH PASSWORD 'choose_a_password';
GRANT CONNECT ON DATABASE geospatial_demo TO agent_ro;
GRANT USAGE ON SCHEMA public TO agent_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO agent_ro;
```

The application also checks that generated SQL is a single `SELECT` or `WITH` query.

## 3. Install Python packages

```bash
pip install -r requirements.txt
```

## 4. Configure environment variables

```bash
cp .env.example .env
```

Fill in the PostgreSQL connection and Gemini API key. You can override the model using `GEMINI_MODEL`. Keep `DB_USER` as the read-only runtime role; if you use the optional FTW loader, set `ETL_DB_USER` / `ETL_DB_PASSWORD` to a write-capable database role.

## 5. Test the deterministic tools first

```bash
python tools.py
```

This should print:

- the database schema,
- matching metadata,
- a safe SQL query result,
- a rejected `DELETE`, and
- one deterministic FTW-vs-statistics comparison.

This is the key Phase-2-style idea: the database tools should work without the LLM.

## 6. Run the terminal agent

```bash
python main.py
```

Example questions:

```text
Which country-year has the largest percentage difference between FTW field area and reported cropland area?

Show the FTW field count, average confidence, and agricultural statistic for EX in 2024.

Which records have average FTW confidence below 75?

What datasets are represented in this database?
```

## 7. Optional: replace demo FTW summaries with real FTW data

The helper script can aggregate one FTW country partition remotely with DuckDB and insert the summary into PostgreSQL.

Example pattern (France is shown only as an example of the FTW partition naming convention):

```bash
python scripts/load_ftw_summary.py \
  --country-code FR \
  --country-name France \
  --parquet-url "s3://us-west-2.opendata.source.coop/ftw/global-data/predictions/vectors/alpha/results-by-admin-conf/admin:country_code=FR/France.parquet"
```

The script reads only these FTW fields:

- `determination:datetime`
- `confidence`
- `metrics:area`

and stores:

- field count,
- total field area in hectares,
- average confidence,
- source URL.

Students can then add their own FAOSTAT ingestion logic and decide how to reconcile country codes, years, units, missing values, and indicator definitions.

## How students can extend this starter

Good next steps include:

- replace the placeholder statistics with real FAOSTAT data;
- add more metadata and provenance;
- add a `verify_result()` tool;
- add PostGIS and spatial queries for a selected region;
- compare multiple cropland maps;
- create a small web UI;
- build an evaluation set with ground-truth SQL.

Those are intentionally left as student work.
