-- Minimal relational schema for a CSE 412 geospatial-agent teaching demo.
-- Intentionally country/year level so the starter stays small and understandable.

CREATE TABLE IF NOT EXISTS country (
    country_code VARCHAR(3) PRIMARY KEY,
    country_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS ftw_country_summary (
    country_code VARCHAR(3) NOT NULL REFERENCES country(country_code),
    year INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100),
    field_count BIGINT NOT NULL CHECK (field_count >= 0),
    total_field_area_ha DOUBLE PRECISION NOT NULL CHECK (total_field_area_ha >= 0),
    avg_confidence DOUBLE PRECISION CHECK (avg_confidence BETWEEN 0 AND 100),
    source_url TEXT NOT NULL,
    PRIMARY KEY (country_code, year)
);

CREATE TABLE IF NOT EXISTS agriculture_stat (
    country_code VARCHAR(3) NOT NULL REFERENCES country(country_code),
    year INTEGER NOT NULL CHECK (year BETWEEN 1900 AND 2100),
    indicator TEXT NOT NULL,
    value_ha DOUBLE PRECISION NOT NULL CHECK (value_ha >= 0),
    source_name TEXT NOT NULL,
    source_url TEXT,
    PRIMARY KEY (country_code, year, indicator, source_name)
);

CREATE TABLE IF NOT EXISTS dataset_metadata (
    dataset_name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    spatial_scope TEXT,
    temporal_scope TEXT,
    key_fields TEXT,
    source_url TEXT NOT NULL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_ftw_year
    ON ftw_country_summary(year);

CREATE INDEX IF NOT EXISTS idx_agri_indicator_year
    ON agriculture_stat(indicator, year);
