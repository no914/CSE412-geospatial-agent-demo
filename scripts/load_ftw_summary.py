import argparse
import os

import duckdb
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_pg_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "geospatial_demo"),
        user=os.getenv("ETL_DB_USER", os.getenv("DB_USER", "agent_ro")),
        password=os.getenv("ETL_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
    )


def aggregate_ftw(parquet_url):
    safe_url = parquet_url.replace("'", "''")
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL spatial; LOAD spatial;")

    query = f"""
        SELECT
            EXTRACT(YEAR FROM "determination:datetime")::INTEGER AS year,
            COUNT(*)::BIGINT AS field_count,
            SUM("metrics:area") / 10000.0 AS total_field_area_ha,
            AVG(confidence) AS avg_confidence
        FROM read_parquet('{safe_url}')
        GROUP BY 1
        ORDER BY 1
    """
    return con.execute(query).fetchall()


def upsert(country_code, country_name, parquet_url, rows):
    conn = get_pg_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO country (country_code, country_name)
                VALUES (%s, %s)
                ON CONFLICT (country_code)
                DO UPDATE SET country_name = EXCLUDED.country_name
                """,
                (country_code, country_name),
            )

            for year, field_count, total_area_ha, avg_confidence in rows:
                cur.execute(
                    """
                    INSERT INTO ftw_country_summary
                        (country_code, year, field_count, total_field_area_ha,
                         avg_confidence, source_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (country_code, year)
                    DO UPDATE SET
                        field_count = EXCLUDED.field_count,
                        total_field_area_ha = EXCLUDED.total_field_area_ha,
                        avg_confidence = EXCLUDED.avg_confidence,
                        source_url = EXCLUDED.source_url
                    """,
                    (
                        country_code,
                        year,
                        field_count,
                        total_area_ha,
                        avg_confidence,
                        parquet_url,
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--country-code", required=True)
    parser.add_argument("--country-name", required=True)
    parser.add_argument("--parquet-url", required=True)
    args = parser.parse_args()

    rows = aggregate_ftw(args.parquet_url)
    if not rows:
        raise SystemExit("No FTW rows found in that partition.")

    print("Aggregated FTW rows:")
    for row in rows:
        print(row)

    upsert(
        args.country_code.upper(),
        args.country_name,
        args.parquet_url,
        rows,
    )
    print("Inserted/updated PostgreSQL summary rows.")


if __name__ == "__main__":
    main()
