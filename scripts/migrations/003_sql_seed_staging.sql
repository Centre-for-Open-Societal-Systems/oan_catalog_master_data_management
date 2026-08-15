BEGIN;

-- Compatibility tables for the inherited SQL source files. These are staging
-- tables only; registries consume canonical release tables through the API.
CREATE TABLE IF NOT EXISTS g2p_crop (
    id                           SERIAL PRIMARY KEY,
    name                         VARCHAR NOT NULL,
    description                  TEXT,
    category_id                  INTEGER,
    known_for                    TEXT,
    num_field_inspection_needed  INTEGER,
    isolation_distance           INTEGER,
    preferred_ecological_zone_id INTEGER
);

CREATE TABLE IF NOT EXISTS g2p_livestock_type (
    id           SERIAL PRIMARY KEY,
    species_code VARCHAR NOT NULL UNIQUE,
    name         VARCHAR,
    description  TEXT,
    icon_url     VARCHAR,
    dataset_id   INTEGER
);

CREATE INDEX IF NOT EXISTS ix_g2p_livestock_type_species_code
    ON g2p_livestock_type (species_code);

CREATE TABLE IF NOT EXISTS g2p_livestock_population (
    id                  SERIAL PRIMARY KEY,
    species_code        INTEGER NOT NULL REFERENCES g2p_livestock_type(id),
    census_year         INTEGER NOT NULL,
    population_total    BIGINT NOT NULL,
    source_record_count INTEGER,
    create_date         TIMESTAMPTZ,
    write_date          TIMESTAMPTZ,
    CONSTRAINT uq_g2p_livestock_population_species_year
        UNIQUE (species_code, census_year)
);

CREATE INDEX IF NOT EXISTS ix_g2p_livestock_population_species
    ON g2p_livestock_population (species_code);

CREATE TABLE IF NOT EXISTS g2p_region (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR NOT NULL UNIQUE,
    name        VARCHAR NOT NULL,
    admin0_name VARCHAR,
    admin0_pcod VARCHAR,
    admin1_pcod VARCHAR,
    admin1_refn VARCHAR
);

CREATE INDEX IF NOT EXISTS ix_g2p_region_code ON g2p_region (code);

CREATE TABLE IF NOT EXISTS g2p_zone (
    id           SERIAL PRIMARY KEY,
    code         VARCHAR NOT NULL UNIQUE,
    name         VARCHAR NOT NULL,
    admin2_pcod  VARCHAR,
    admin2_refn  VARCHAR,
    admin2_altn  VARCHAR,
    admin2_al_1  VARCHAR,
    lat          NUMERIC(15, 11),
    long         NUMERIC(15, 11),
    shape_length NUMERIC(20, 12),
    shape_area   NUMERIC(20, 15),
    region       INTEGER NOT NULL REFERENCES g2p_region(id)
);

CREATE INDEX IF NOT EXISTS ix_g2p_zone_code ON g2p_zone (code);
CREATE INDEX IF NOT EXISTS ix_g2p_zone_region ON g2p_zone (region);

CREATE TABLE IF NOT EXISTS g2p_woreda (
    id           SERIAL PRIMARY KEY,
    code         VARCHAR NOT NULL UNIQUE,
    name         VARCHAR NOT NULL,
    admin3_pcod  VARCHAR,
    admin3_refn  VARCHAR,
    admin3_altn  VARCHAR,
    admin3_al_1  VARCHAR,
    shape_length NUMERIC(20, 12),
    shape_area   NUMERIC(20, 15),
    zone         INTEGER REFERENCES g2p_zone(id)
);

CREATE INDEX IF NOT EXISTS ix_g2p_woreda_code ON g2p_woreda (code);
CREATE INDEX IF NOT EXISTS ix_g2p_woreda_zone ON g2p_woreda (zone);

CREATE TABLE IF NOT EXISTS g2p_seed_catalog (
    id   SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS g2p_seed_demand_summary (
    id                         SERIAL PRIMARY KEY,
    budget_year                INTEGER NOT NULL,
    total_entries              INTEGER NOT NULL,
    total_quantity_demanded    NUMERIC(20, 4) NOT NULL,
    average_quantity_per_entry NUMERIC(20, 4) NOT NULL,
    total_estimated_land_ha     NUMERIC(20, 4) NOT NULL,
    average_estimated_land_ha   NUMERIC(20, 4) NOT NULL,
    CONSTRAINT uq_g2p_seed_demand_summary_year
        UNIQUE (budget_year)
);

CREATE TABLE IF NOT EXISTS g2p_seed_demand_trend (
    id                  SERIAL PRIMARY KEY,
    budget_year         INTEGER NOT NULL,
    seed_class          VARCHAR NOT NULL,
    quantity_demanded   NUMERIC(20, 4) NOT NULL,
    CONSTRAINT uq_g2p_seed_demand_trend_year_class
        UNIQUE (budget_year, seed_class)
);

CREATE TABLE IF NOT EXISTS g2p_seed_demand_trend_by_crop (
    id                SERIAL PRIMARY KEY,
    crop_id           INTEGER NOT NULL,
    crop_name         VARCHAR NOT NULL,
    budget_year       INTEGER NOT NULL,
    seed_class        VARCHAR NOT NULL,
    quantity_demanded NUMERIC(20, 4) NOT NULL,
    CONSTRAINT uq_g2p_seed_demand_crop_year_class
        UNIQUE (crop_id, budget_year, seed_class)
);

CREATE INDEX IF NOT EXISTS ix_g2p_seed_demand_crop_id
    ON g2p_seed_demand_trend_by_crop (crop_id);

COMMIT;
