import re

from db import run_query

BLOCKED_WORDS = {
    "insert", "update", "delete", "drop", "alter", "create",
    "truncate", "grant", "revoke", "copy", "vacuum", "comment",
}


def _format_table(columns, rows):
    if not rows:
        return "No rows returned."
    lines = [" | ".join(columns)]
    for row in rows:
        lines.append(" | ".join("NULL" if v is None else str(v) for v in row))
    lines.append(f"({len(rows)} rows shown)")
    return "\n".join(lines)


def get_database_schema():
    """Return public tables, columns, data types, primary keys, and foreign keys."""
    column_sql = """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position
    """

    constraint_sql = """
        SELECT conrelid::regclass::text AS table_name,
               contype,
               pg_get_constraintdef(oid) AS definition
        FROM pg_constraint
        WHERE connamespace = 'public'::regnamespace
          AND contype IN ('p', 'f')
        ORDER BY conrelid::regclass::text, contype
    """

    _, columns = run_query(column_sql, max_rows=500)
    _, constraints = run_query(constraint_sql, max_rows=200)

    by_table = {}
    for table, column, dtype, nullable in columns:
        marker = "NULL" if nullable == "YES" else "NOT NULL"
        by_table.setdefault(table, []).append(f"{column} {dtype} {marker}")

    lines = []
    for table, fields in by_table.items():
        lines.append(f"TABLE {table} ({', '.join(fields)})")

    for table, contype, definition in constraints:
        label = "PK" if contype == "p" else "FK"
        lines.append(f"{label} {table}: {definition}")

    return "\n".join(lines)


def search_metadata(query):
    """Search dataset descriptions/notes using case-insensitive keyword matching."""
    tokens = [t for t in re.findall(r"[A-Za-z0-9_-]+", query) if len(t) >= 2]
    if not tokens:
        return "Please provide at least one metadata keyword."

    where_parts = []
    params = []
    for token in tokens[:5]:
        pattern = f"%{token}%"
        where_parts.append(
            "(dataset_name ILIKE %s OR description ILIKE %s OR "
            "key_fields ILIKE %s OR notes ILIKE %s)"
        )
        params.extend([pattern, pattern, pattern, pattern])

    sql = f"""
        SELECT dataset_name, description, spatial_scope, temporal_scope,
               key_fields, source_url, notes
        FROM dataset_metadata
        WHERE {' OR '.join(where_parts)}
        ORDER BY dataset_name
    """
    columns, rows = run_query(sql, params=params, max_rows=20)
    return _format_table(columns, rows)


def is_safe_sql(sql):
    """Allow one read-only SELECT/CTE statement; reject obvious DDL/DML."""
    cleaned = sql.strip().rstrip(";").strip()
    if not cleaned:
        return False, "empty query"
    if ";" in cleaned:
        return False, "multiple SQL statements are not allowed"

    lowered = cleaned.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False, "only SELECT or WITH queries are allowed"

    words = set(re.findall(r"[a-z_]+", lowered))
    blocked = sorted(words & BLOCKED_WORDS)
    if blocked:
        return False, f"blocked keyword: {blocked[0]}"

    return True, ""


def execute_sql(sql, max_rows=100):
    """Run one safe, read-only query and return the rows as text."""
    ok, reason = is_safe_sql(sql)
    if not ok:
        return f"REJECTED: {reason}"

    try:
        columns, rows = run_query(sql, max_rows=max_rows)
        return _format_table(columns, rows)
    except Exception as exc:
        return f"ERROR: {exc}"


def compare_country_year(country_code, year):
    """Deterministically compare FTW area with a cropland statistic for one country/year."""
    sql = """
        SELECT c.country_name,
               f.country_code,
               f.year,
               f.field_count,
               ROUND(f.total_field_area_ha::numeric, 2) AS ftw_area_ha,
               ROUND(f.avg_confidence::numeric, 2) AS avg_confidence,
               ROUND(a.value_ha::numeric, 2) AS reported_area_ha,
               ROUND((f.total_field_area_ha - a.value_ha)::numeric, 2) AS difference_ha,
               ROUND(
                   (100.0 * (f.total_field_area_ha - a.value_ha)
                    / NULLIF(a.value_ha, 0))::numeric,
                   2
               ) AS pct_difference
        FROM ftw_country_summary f
        JOIN country c USING (country_code)
        JOIN agriculture_stat a
          ON a.country_code = f.country_code
         AND a.year = f.year
         AND a.indicator = 'cropland_area'
        WHERE f.country_code = %s AND f.year = %s
    """
    columns, rows = run_query(sql, params=(country_code.upper(), int(year)), max_rows=10)
    if not rows:
        return "No integrated FTW/agricultural-statistics row found for that country/year."
    return _format_table(columns, rows)


if __name__ == "__main__":
    print("=== SCHEMA ===")
    print(get_database_schema())

    print("\n=== METADATA SEARCH ===")
    print(search_metadata("FTW confidence"))

    print("\n=== SAFE QUERY ===")
    print(execute_sql("SELECT country_code, year, avg_confidence FROM ftw_country_summary ORDER BY avg_confidence LIMIT 5"))

    print("\n=== UNSAFE QUERY (should be rejected) ===")
    print(execute_sql("DELETE FROM ftw_country_summary"))

    print("\n=== DETERMINISTIC COMPARISON ===")
    print(compare_country_year("EX", 2024))
