BEGIN;

ALTER TABLE g2p_livestock_type
    ADD COLUMN scientific_name TEXT,
    ADD COLUMN subfamily TEXT,
    ADD COLUMN species_type_code INTEGER,
    ADD COLUMN chart_color VARCHAR,
    ADD COLUMN ear_tag_range TEXT,
    ADD COLUMN in_lis_population BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN in_etlits_registry BOOLEAN NOT NULL DEFAULT FALSE,
    ADD CONSTRAINT ck_g2p_livestock_type_species_code_lowercase
        CHECK (species_code = lower(species_code)),
    ADD CONSTRAINT ck_g2p_livestock_type_species_type_code
        CHECK (species_type_code IS NULL OR species_type_code > 0);

CREATE TABLE g2p_livestock_breed (
    id                   INTEGER PRIMARY KEY,
    breed_code           VARCHAR UNIQUE,
    name                 VARCHAR NOT NULL,
    abbreviation         VARCHAR,
    species_id           INTEGER NOT NULL REFERENCES g2p_livestock_type(id),
    breed_type           VARCHAR NOT NULL,
    in_national_standard BOOLEAN NOT NULL DEFAULT TRUE,
    in_etlits_registry   BOOLEAN NOT NULL DEFAULT FALSE,
    source               TEXT NOT NULL,
    CONSTRAINT uq_g2p_livestock_breed_species_name UNIQUE (species_id, name),
    CONSTRAINT ck_g2p_livestock_breed_type
        CHECK (breed_type IN ('Indigenous', 'Exotic', 'Cross'))
);

CREATE INDEX ix_g2p_livestock_breed_species
    ON g2p_livestock_breed (species_id);
CREATE INDEX ix_g2p_livestock_breed_name
    ON g2p_livestock_breed (name);
CREATE INDEX ix_g2p_livestock_breed_type
    ON g2p_livestock_breed (breed_type);

CREATE TABLE g2p_livestock_gender (
    code               VARCHAR PRIMARY KEY,
    name               VARCHAR NOT NULL,
    description        TEXT,
    in_etlits_registry BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE g2p_livestock_location_type (
    code                          VARCHAR PRIMARY KEY,
    name                          VARCHAR NOT NULL,
    ethiopian_zone_name          VARCHAR,
    altitude_description          TEXT,
    ecological_zone_id            INTEGER
                                  REFERENCES g2p_ecological_zone(id),
    description                   TEXT
);

CREATE INDEX ix_g2p_livestock_location_ecological_zone
    ON g2p_livestock_location_type (ecological_zone_id);

CREATE TABLE g2p_livestock_body_condition (
    code            VARCHAR PRIMARY KEY,
    bcs_score       INTEGER NOT NULL UNIQUE,
    condition_label VARCHAR NOT NULL,
    fatness_label   VARCHAR NOT NULL,
    etlits_label    VARCHAR UNIQUE,
    description     TEXT,
    CONSTRAINT ck_g2p_livestock_body_condition_score
        CHECK (bcs_score BETWEEN 1 AND 5)
);

CREATE TABLE g2p_livestock_production_type (
    code                 VARCHAR PRIMARY KEY,
    name                 VARCHAR NOT NULL,
    standard_purpose     VARCHAR,
    in_national_standard BOOLEAN NOT NULL DEFAULT FALSE,
    in_etlits_registry   BOOLEAN NOT NULL DEFAULT FALSE,
    description          TEXT
);

CREATE TABLE g2p_livestock_production_type_species (
    production_type_code VARCHAR NOT NULL
                         REFERENCES g2p_livestock_production_type(code)
                         ON DELETE CASCADE,
    species_id           INTEGER NOT NULL
                         REFERENCES g2p_livestock_type(id)
                         ON DELETE CASCADE,
    PRIMARY KEY (production_type_code, species_id)
);

CREATE INDEX ix_g2p_livestock_production_species
    ON g2p_livestock_production_type_species (species_id);

CREATE TABLE g2p_livestock_record_status (
    code                VARCHAR PRIMARY KEY,
    name                VARCHAR NOT NULL,
    sort_order          INTEGER NOT NULL UNIQUE,
    is_live_master_data BOOLEAN NOT NULL DEFAULT FALSE,
    description         TEXT,
    CONSTRAINT ck_g2p_livestock_record_status_sort_order
        CHECK (sort_order > 0)
);

COMMIT;
