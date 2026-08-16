BEGIN;

CREATE TABLE crop_variety_source_records (
    variety_source_record_id VARCHAR PRIMARY KEY,
    release_id               VARCHAR NOT NULL
                             REFERENCES catalogue_releases(release_id) ON DELETE CASCADE,
    variety_value_id         VARCHAR NOT NULL
                             REFERENCES catalogue_values(catalogue_value_id) ON DELETE CASCADE,
    source_record_code       VARCHAR NOT NULL,
    source_row_number        INTEGER,
    centre                   TEXT NOT NULL,
    release_year_raw         VARCHAR NOT NULL,
    release_year             SMALLINT,
    source_url               TEXT,
    altitude_min_m           NUMERIC(12, 4),
    altitude_max_m           NUMERIC(12, 4),
    rainfall_min_mm          NUMERIC(12, 4),
    rainfall_max_mm          NUMERIC(12, 4),
    days_to_maturity_min     INTEGER,
    days_to_maturity_max     INTEGER,
    yield_research_min_qt_ha NUMERIC(16, 4),
    yield_research_max_qt_ha NUMERIC(16, 4),
    yield_farmer_min_qt_ha   NUMERIC(16, 4),
    yield_farmer_max_qt_ha   NUMERIC(16, 4),
    seed_rate_kg_ha          NUMERIC(16, 4),
    adaptation_area          TEXT,
    planting_date_text       TEXT,
    crop_pest_reaction       TEXT,
    CONSTRAINT uq_crop_variety_source_release_code
        UNIQUE (release_id, source_record_code),
    CONSTRAINT uq_crop_variety_source_release_row
        UNIQUE (release_id, source_row_number),
    CONSTRAINT ck_crop_variety_source_row
        CHECK (source_row_number IS NULL OR source_row_number > 0),
    CONSTRAINT ck_crop_variety_source_release_year
        CHECK (release_year IS NULL OR release_year BETWEEN 1800 AND 2200),
    CONSTRAINT ck_crop_variety_source_altitude_range
        CHECK (altitude_min_m IS NULL OR altitude_max_m IS NULL
               OR altitude_max_m >= altitude_min_m),
    CONSTRAINT ck_crop_variety_source_rainfall_range
        CHECK (rainfall_min_mm IS NULL OR rainfall_max_mm IS NULL
               OR rainfall_max_mm >= rainfall_min_mm),
    CONSTRAINT ck_crop_variety_source_maturity_range
        CHECK (days_to_maturity_min IS NULL OR days_to_maturity_max IS NULL
               OR days_to_maturity_max >= days_to_maturity_min),
    CONSTRAINT ck_crop_variety_source_research_yield_range
        CHECK (yield_research_min_qt_ha IS NULL OR yield_research_max_qt_ha IS NULL
               OR yield_research_max_qt_ha >= yield_research_min_qt_ha),
    CONSTRAINT ck_crop_variety_source_farmer_yield_range
        CHECK (yield_farmer_min_qt_ha IS NULL OR yield_farmer_max_qt_ha IS NULL
               OR yield_farmer_max_qt_ha >= yield_farmer_min_qt_ha)
);

CREATE INDEX ix_crop_variety_source_release_variety
    ON crop_variety_source_records (release_id, variety_value_id);
CREATE INDEX ix_crop_variety_source_release_year
    ON crop_variety_source_records (release_id, release_year);

CREATE TABLE crop_characteristic_definitions (
    characteristic_definition_id VARCHAR PRIMARY KEY,
    release_id                    VARCHAR NOT NULL
                                  REFERENCES catalogue_releases(release_id) ON DELETE CASCADE,
    characteristic_code          VARCHAR NOT NULL,
    display_name                 VARCHAR NOT NULL,
    value_type                   VARCHAR NOT NULL,
    default_unit_code            VARCHAR,
    applicable_category_value_id VARCHAR
                                  REFERENCES catalogue_values(catalogue_value_id) ON DELETE CASCADE,
    description                  TEXT,
    CONSTRAINT uq_crop_characteristic_release_code
        UNIQUE (release_id, characteristic_code),
    CONSTRAINT ck_crop_characteristic_value_type
        CHECK (value_type IN ('TEXT', 'INTEGER', 'DECIMAL', 'BOOLEAN', 'RANGE'))
);

CREATE INDEX ix_crop_characteristic_release_category
    ON crop_characteristic_definitions (release_id, applicable_category_value_id);

CREATE TABLE crop_variety_characteristics (
    variety_source_record_id       VARCHAR NOT NULL
                                   REFERENCES crop_variety_source_records(variety_source_record_id)
                                   ON DELETE CASCADE,
    characteristic_definition_id   VARCHAR NOT NULL
                                   REFERENCES crop_characteristic_definitions(characteristic_definition_id)
                                   ON DELETE CASCADE,
    raw_value                      TEXT NOT NULL,
    value_text                     TEXT,
    value_numeric                  NUMERIC(24, 8),
    value_boolean                  BOOLEAN,
    value_min                      NUMERIC(24, 8),
    value_max                      NUMERIC(24, 8),
    unit_code                      VARCHAR,
    PRIMARY KEY (variety_source_record_id, characteristic_definition_id),
    CONSTRAINT ck_crop_variety_characteristic_value_range
        CHECK (value_min IS NULL OR value_max IS NULL OR value_max >= value_min)
);

CREATE INDEX ix_crop_variety_characteristic_definition
    ON crop_variety_characteristics (characteristic_definition_id);

COMMIT;
