BEGIN;

CREATE TABLE IF NOT EXISTS geography_levels (
    geography_level_id VARCHAR PRIMARY KEY,
    release_id         VARCHAR NOT NULL
                       REFERENCES catalogue_releases(release_id) ON DELETE CASCADE,
    code               VARCHAR NOT NULL,
    display_name       VARCHAR NOT NULL,
    display_name_i18n  JSONB,
    level_order        INTEGER NOT NULL,
    parent_level_id    VARCHAR REFERENCES geography_levels(geography_level_id),
    CONSTRAINT uq_geography_level_release_code UNIQUE (release_id, code),
    CONSTRAINT uq_geography_level_release_order UNIQUE (release_id, level_order),
    CONSTRAINT ck_geography_level_order CHECK (level_order >= 0)
);

CREATE INDEX IF NOT EXISTS ix_geography_levels_release ON geography_levels (release_id);
CREATE INDEX IF NOT EXISTS ix_geography_levels_parent ON geography_levels (parent_level_id);

CREATE TABLE IF NOT EXISTS geography_units (
    geography_unit_id  VARCHAR PRIMARY KEY,
    geography_level_id VARCHAR NOT NULL
                       REFERENCES geography_levels(geography_level_id) ON DELETE CASCADE,
    code               VARCHAR NOT NULL,
    display_name       VARCHAR NOT NULL,
    display_name_i18n  JSONB,
    parent_unit_id     VARCHAR REFERENCES geography_units(geography_unit_id),
    latitude           NUMERIC(12, 8),
    longitude          NUMERIC(12, 8),
    valid_from         DATE,
    valid_to           DATE,
    status             VARCHAR NOT NULL DEFAULT 'ACTIVE',
    aliases            JSONB,
    metadata           JSONB,
    CONSTRAINT uq_geography_unit_level_code UNIQUE (geography_level_id, code),
    CONSTRAINT ck_geography_unit_dates
        CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

CREATE INDEX IF NOT EXISTS ix_geography_units_level ON geography_units (geography_level_id);
CREATE INDEX IF NOT EXISTS ix_geography_units_code ON geography_units (code);
CREATE INDEX IF NOT EXISTS ix_geography_units_parent ON geography_units (parent_unit_id);
CREATE INDEX IF NOT EXISTS ix_geography_units_status ON geography_units (status);

CREATE TABLE IF NOT EXISTS livestock_population_statistics (
    statistic_id        VARCHAR PRIMARY KEY,
    release_id          VARCHAR NOT NULL
                        REFERENCES catalogue_releases(release_id) ON DELETE CASCADE,
    species_code        VARCHAR NOT NULL,
    census_year         INTEGER NOT NULL,
    population_total    BIGINT NOT NULL,
    source_record_count INTEGER,
    source              VARCHAR,
    CONSTRAINT uq_livestock_stat_release_species_year
        UNIQUE (release_id, species_code, census_year)
);

CREATE INDEX IF NOT EXISTS ix_livestock_stats_release
    ON livestock_population_statistics (release_id);
CREATE INDEX IF NOT EXISTS ix_livestock_stats_species
    ON livestock_population_statistics (species_code);

CREATE TABLE IF NOT EXISTS seed_demand_summary_statistics (
    statistic_id                VARCHAR PRIMARY KEY,
    release_id                  VARCHAR NOT NULL
                                REFERENCES catalogue_releases(release_id) ON DELETE CASCADE,
    budget_year                 INTEGER NOT NULL,
    total_entries               INTEGER NOT NULL,
    total_quantity_demanded     NUMERIC(20, 4) NOT NULL,
    average_quantity_per_entry  NUMERIC(20, 4) NOT NULL,
    total_estimated_land_ha      NUMERIC(20, 4) NOT NULL,
    average_estimated_land_ha    NUMERIC(20, 4) NOT NULL,
    CONSTRAINT uq_seed_summary_release_year UNIQUE (release_id, budget_year)
);

CREATE INDEX IF NOT EXISTS ix_seed_summary_release
    ON seed_demand_summary_statistics (release_id);

CREATE TABLE IF NOT EXISTS seed_demand_trend_statistics (
    statistic_id      VARCHAR PRIMARY KEY,
    release_id        VARCHAR NOT NULL
                      REFERENCES catalogue_releases(release_id) ON DELETE CASCADE,
    budget_year       INTEGER NOT NULL,
    seed_class        VARCHAR NOT NULL,
    quantity_demanded NUMERIC(20, 4) NOT NULL,
    CONSTRAINT uq_seed_trend_release_year_class
        UNIQUE (release_id, budget_year, seed_class)
);

CREATE INDEX IF NOT EXISTS ix_seed_trend_release
    ON seed_demand_trend_statistics (release_id);

CREATE TABLE IF NOT EXISTS seed_demand_by_crop_statistics (
    statistic_id      VARCHAR PRIMARY KEY,
    release_id        VARCHAR NOT NULL
                      REFERENCES catalogue_releases(release_id) ON DELETE CASCADE,
    crop_code         VARCHAR NOT NULL,
    crop_name         VARCHAR NOT NULL,
    budget_year       INTEGER NOT NULL,
    seed_class        VARCHAR NOT NULL,
    quantity_demanded NUMERIC(20, 4) NOT NULL,
    CONSTRAINT uq_seed_crop_stat_release_crop_year_class
        UNIQUE (release_id, crop_code, budget_year, seed_class)
);

CREATE INDEX IF NOT EXISTS ix_seed_crop_stats_release
    ON seed_demand_by_crop_statistics (release_id);
CREATE INDEX IF NOT EXISTS ix_seed_crop_stats_code
    ON seed_demand_by_crop_statistics (crop_code);

COMMIT;
