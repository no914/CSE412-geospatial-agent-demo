-- IMPORTANT: These values are intentionally illustrative placeholders.
-- They are NOT real FTW or FAOSTAT measurements and must not be cited as results.

INSERT INTO country (country_code, country_name) VALUES
    ('EX', 'Exampleland'),
    ('DY', 'Demo Republic'),
    ('ZZ', 'Sample State')
ON CONFLICT DO NOTHING;

INSERT INTO ftw_country_summary
(country_code, year, field_count, total_field_area_ha, avg_confidence, source_url)
VALUES
    ('EX', 2024, 125000, 980000.0, 86.5, 'https://source.coop/ftw/global-data'),
    ('DY', 2024,  93000, 720000.0, 71.2, 'https://source.coop/ftw/global-data'),
    ('ZZ', 2024, 148000, 860000.0, 78.9, 'https://source.coop/ftw/global-data'),
    ('EX', 2025, 127500, 995000.0, 87.1, 'https://source.coop/ftw/global-data')
ON CONFLICT (country_code, year) DO UPDATE SET
    field_count = EXCLUDED.field_count,
    total_field_area_ha = EXCLUDED.total_field_area_ha,
    avg_confidence = EXCLUDED.avg_confidence,
    source_url = EXCLUDED.source_url;

INSERT INTO agriculture_stat
(country_code, year, indicator, value_ha, source_name, source_url)
VALUES
    ('EX', 2024, 'cropland_area', 1040000.0, 'Demo agricultural statistics', 'https://www.fao.org/faostat/en/#data/RL'),
    ('DY', 2024, 'cropland_area',  900000.0, 'Demo agricultural statistics', 'https://www.fao.org/faostat/en/#data/RL'),
    ('ZZ', 2024, 'cropland_area',  820000.0, 'Demo agricultural statistics', 'https://www.fao.org/faostat/en/#data/RL'),
    ('EX', 2025, 'cropland_area', 1060000.0, 'Demo agricultural statistics', 'https://www.fao.org/faostat/en/#data/RL')
ON CONFLICT (country_code, year, indicator, source_name) DO UPDATE SET
    value_ha = EXCLUDED.value_ha,
    source_url = EXCLUDED.source_url;

INSERT INTO dataset_metadata
(dataset_name, description, spatial_scope, temporal_scope, key_fields, source_url, notes)
VALUES
(
    'Fields of The World (FTW)',
    'Model-derived agricultural field-boundary predictions. This starter stores country/year aggregates rather than raw polygons.',
    'Global; original data are partitioned by country/admin region',
    '2024-2025 in the current global collection',
    'country_code, year, field_count, total_field_area_ha, avg_confidence',
    'https://source.coop/ftw/global-data',
    'FTW field units are remote-sensing predictions, not legal parcels.'
),
(
    'Agricultural statistics',
    'National agricultural land statistics used as a second heterogeneous data source for integration examples.',
    'Country level',
    'Depends on the selected source/table',
    'country_code, year, indicator, value_ha',
    'https://www.fao.org/faostat/en/',
    'Students should document the exact FAOSTAT table, indicator definition, unit conversion, and country-code mapping they use.'
)
ON CONFLICT (dataset_name) DO UPDATE SET
    description = EXCLUDED.description,
    spatial_scope = EXCLUDED.spatial_scope,
    temporal_scope = EXCLUDED.temporal_scope,
    key_fields = EXCLUDED.key_fields,
    source_url = EXCLUDED.source_url,
    notes = EXCLUDED.notes;
