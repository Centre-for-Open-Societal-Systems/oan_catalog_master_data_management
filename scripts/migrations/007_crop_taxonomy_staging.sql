BEGIN;

CREATE TABLE g2p_crop_taxonomy_category (
    category_code     VARCHAR PRIMARY KEY,
    source_id         VARCHAR NOT NULL UNIQUE,
    display_name      VARCHAR NOT NULL,
    display_name_i18n JSONB,
    image_url         TEXT,
    description       TEXT,
    status            VARCHAR NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT ck_g2p_crop_taxonomy_category_status
        CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE TABLE g2p_crop_taxonomy_type (
    type_code                     VARCHAR PRIMARY KEY,
    source_id                     VARCHAR UNIQUE,
    category_code                 VARCHAR NOT NULL
                                  REFERENCES g2p_crop_taxonomy_category(category_code),
    display_name                  VARCHAR NOT NULL,
    display_name_i18n             JSONB,
    scientific_name               TEXT,
    centre                        TEXT,
    image_url                     TEXT,
    description                   TEXT,
    source_reported_variety_count INTEGER,
    status                        VARCHAR NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT uq_g2p_crop_taxonomy_type_category_name
        UNIQUE (category_code, display_name),
    CONSTRAINT ck_g2p_crop_taxonomy_type_variety_count
        CHECK (source_reported_variety_count IS NULL OR source_reported_variety_count >= 0),
    CONSTRAINT ck_g2p_crop_taxonomy_type_status
        CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE INDEX ix_g2p_crop_taxonomy_type_category
    ON g2p_crop_taxonomy_type (category_code);

CREATE TABLE g2p_crop_variety (
    variety_code      VARCHAR PRIMARY KEY,
    type_code         VARCHAR NOT NULL REFERENCES g2p_crop_taxonomy_type(type_code),
    display_name      VARCHAR NOT NULL,
    display_name_i18n JSONB,
    status            VARCHAR NOT NULL DEFAULT 'ACTIVE',
    CONSTRAINT uq_g2p_crop_variety_type_name UNIQUE (type_code, display_name),
    CONSTRAINT ck_g2p_crop_variety_status CHECK (status IN ('ACTIVE', 'INACTIVE'))
);

CREATE INDEX ix_g2p_crop_variety_type ON g2p_crop_variety (type_code);

CREATE TABLE g2p_crop_variety_source_record (
    source_record_code          VARCHAR PRIMARY KEY,
    variety_code                VARCHAR NOT NULL REFERENCES g2p_crop_variety(variety_code),
    source_row_number           INTEGER UNIQUE,
    centre                      TEXT NOT NULL,
    release_year_raw            VARCHAR NOT NULL,
    release_year                SMALLINT,
    source_url                  TEXT,
    altitude_min_m              NUMERIC(12, 4),
    altitude_max_m              NUMERIC(12, 4),
    rainfall_min_mm             NUMERIC(12, 4),
    rainfall_max_mm             NUMERIC(12, 4),
    days_to_maturity_min        INTEGER,
    days_to_maturity_max        INTEGER,
    yield_research_min_qt_ha    NUMERIC(16, 4),
    yield_research_max_qt_ha    NUMERIC(16, 4),
    yield_farmer_min_qt_ha      NUMERIC(16, 4),
    yield_farmer_max_qt_ha      NUMERIC(16, 4),
    seed_rate_kg_ha             NUMERIC(16, 4),
    adaptation_area             TEXT,
    planting_date_text          TEXT,
    crop_pest_reaction          TEXT,
    CONSTRAINT ck_g2p_crop_variety_source_row
        CHECK (source_row_number IS NULL OR source_row_number > 0),
    CONSTRAINT ck_g2p_crop_variety_release_year
        CHECK (release_year IS NULL OR release_year BETWEEN 1800 AND 2200),
    CONSTRAINT ck_g2p_crop_variety_altitude_range
        CHECK (altitude_min_m IS NULL OR altitude_max_m IS NULL OR altitude_max_m >= altitude_min_m),
    CONSTRAINT ck_g2p_crop_variety_rainfall_range
        CHECK (rainfall_min_mm IS NULL OR rainfall_max_mm IS NULL OR rainfall_max_mm >= rainfall_min_mm),
    CONSTRAINT ck_g2p_crop_variety_maturity_range
        CHECK (days_to_maturity_min IS NULL OR days_to_maturity_max IS NULL
               OR days_to_maturity_max >= days_to_maturity_min),
    CONSTRAINT ck_g2p_crop_variety_research_yield_range
        CHECK (yield_research_min_qt_ha IS NULL OR yield_research_max_qt_ha IS NULL
               OR yield_research_max_qt_ha >= yield_research_min_qt_ha),
    CONSTRAINT ck_g2p_crop_variety_farmer_yield_range
        CHECK (yield_farmer_min_qt_ha IS NULL OR yield_farmer_max_qt_ha IS NULL
               OR yield_farmer_max_qt_ha >= yield_farmer_min_qt_ha)
);

CREATE INDEX ix_g2p_crop_variety_source_variety
    ON g2p_crop_variety_source_record (variety_code);
CREATE INDEX ix_g2p_crop_variety_source_release_year
    ON g2p_crop_variety_source_record (release_year);

CREATE TABLE g2p_crop_characteristic_definition (
    characteristic_code     VARCHAR PRIMARY KEY,
    display_name            VARCHAR NOT NULL,
    value_type              VARCHAR NOT NULL,
    default_unit_code       VARCHAR,
    applicable_category_code VARCHAR
                             REFERENCES g2p_crop_taxonomy_category(category_code),
    description             TEXT,
    CONSTRAINT ck_g2p_crop_characteristic_value_type
        CHECK (value_type IN ('TEXT', 'INTEGER', 'DECIMAL', 'BOOLEAN', 'RANGE'))
);

CREATE INDEX ix_g2p_crop_characteristic_category
    ON g2p_crop_characteristic_definition (applicable_category_code);

CREATE TABLE g2p_crop_variety_characteristic (
    source_record_code  VARCHAR NOT NULL
                        REFERENCES g2p_crop_variety_source_record(source_record_code)
                        ON DELETE CASCADE,
    characteristic_code VARCHAR NOT NULL
                        REFERENCES g2p_crop_characteristic_definition(characteristic_code),
    raw_value           TEXT NOT NULL,
    value_text          TEXT,
    value_numeric       NUMERIC(24, 8),
    value_boolean       BOOLEAN,
    value_min           NUMERIC(24, 8),
    value_max           NUMERIC(24, 8),
    unit_code           VARCHAR,
    PRIMARY KEY (source_record_code, characteristic_code),
    CONSTRAINT ck_g2p_crop_variety_characteristic_range
        CHECK (value_min IS NULL OR value_max IS NULL OR value_max >= value_min)
);

CREATE INDEX ix_g2p_crop_variety_characteristic_definition
    ON g2p_crop_variety_characteristic (characteristic_code);

COMMIT;
