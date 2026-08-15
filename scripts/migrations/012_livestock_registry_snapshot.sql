BEGIN;

CREATE TABLE g2p_livestock_registry_entry (
    id                   VARCHAR PRIMARY KEY,
    species_code         VARCHAR NOT NULL
                         REFERENCES g2p_livestock_type(species_code),
    breed_name           VARCHAR NOT NULL,
    breed_id             INTEGER REFERENCES g2p_livestock_breed(id),
    gender_code          VARCHAR NOT NULL
                         REFERENCES g2p_livestock_gender(code),
    location_type_code   VARCHAR NOT NULL
                         REFERENCES g2p_livestock_location_type(code),
    body_condition_code  VARCHAR NOT NULL
                         REFERENCES g2p_livestock_body_condition(code),
    production_type_code VARCHAR NOT NULL
                         REFERENCES g2p_livestock_production_type(code),
    status               VARCHAR NOT NULL
                         REFERENCES g2p_livestock_record_status(code),
    created_on           TIMESTAMPTZ NOT NULL,
    updated_on           TIMESTAMPTZ NOT NULL,
    CONSTRAINT ck_g2p_livestock_registry_dates
        CHECK (updated_on >= created_on)
);

CREATE INDEX ix_g2p_livestock_registry_species
    ON g2p_livestock_registry_entry (species_code);
CREATE INDEX ix_g2p_livestock_registry_status
    ON g2p_livestock_registry_entry (status);
CREATE INDEX ix_g2p_livestock_registry_breed
    ON g2p_livestock_registry_entry (breed_id);

CREATE VIEW g2p_livestock_registry_validation AS
SELECT
    registry.id,
    registry.status,
    registry.species_code,
    registry.breed_name,
    breed.breed_code,
    breed_species.species_code AS breed_species_code,
    registry.production_type_code,
    breed.id IS NULL AS breed_unrecognised,
    breed.id IS NOT NULL AND NOT breed.in_national_standard
        AS breed_outside_national_standard,
    breed.id IS NOT NULL AND breed_species.species_code <> registry.species_code
        AS breed_species_mismatch,
    NOT EXISTS (
        SELECT 1
          FROM g2p_livestock_production_type_species valid_species
          JOIN g2p_livestock_type species
            ON species.id = valid_species.species_id
         WHERE valid_species.production_type_code = registry.production_type_code
           AND species.species_code = registry.species_code
    ) AS production_type_species_mismatch
FROM g2p_livestock_registry_entry registry
LEFT JOIN g2p_livestock_breed breed ON breed.id = registry.breed_id
LEFT JOIN g2p_livestock_type breed_species ON breed_species.id = breed.species_id;

CREATE TABLE livestock_registry_entries (
    registry_entry_id             VARCHAR PRIMARY KEY,
    release_id                    VARCHAR NOT NULL
                                  REFERENCES catalogue_releases(release_id)
                                  ON DELETE CASCADE,
    source_entry_id               VARCHAR NOT NULL,
    species_code                  VARCHAR NOT NULL,
    breed_name                    VARCHAR NOT NULL,
    breed_source_id               INTEGER,
    breed_code                    VARCHAR,
    breed_species_code            VARCHAR,
    breed_in_national_standard    BOOLEAN,
    gender_code                   VARCHAR NOT NULL,
    location_type_code            VARCHAR NOT NULL,
    body_condition_code           VARCHAR NOT NULL,
    production_type_code          VARCHAR NOT NULL,
    status                        VARCHAR NOT NULL,
    source_created_on             TIMESTAMPTZ NOT NULL,
    source_updated_on             TIMESTAMPTZ NOT NULL,
    production_type_species_valid BOOLEAN NOT NULL,
    CONSTRAINT uq_livestock_registry_release_source
        UNIQUE (release_id, source_entry_id),
    CONSTRAINT ck_livestock_registry_source_dates
        CHECK (source_updated_on >= source_created_on)
);

CREATE INDEX ix_livestock_registry_entries_release
    ON livestock_registry_entries (release_id);
CREATE INDEX ix_livestock_registry_entries_species
    ON livestock_registry_entries (species_code);
CREATE INDEX ix_livestock_registry_entries_status
    ON livestock_registry_entries (status);
CREATE INDEX ix_livestock_registry_entries_breed
    ON livestock_registry_entries (breed_source_id);

CREATE VIEW livestock_registry_validation AS
SELECT
    registry.release_id,
    registry.source_entry_id AS id,
    registry.status,
    registry.species_code,
    registry.breed_name,
    registry.breed_code,
    registry.breed_species_code,
    registry.production_type_code,
    registry.breed_source_id IS NULL AS breed_unrecognised,
    registry.breed_source_id IS NOT NULL
        AND NOT registry.breed_in_national_standard
        AS breed_outside_national_standard,
    registry.breed_source_id IS NOT NULL
        AND registry.breed_species_code <> registry.species_code
        AS breed_species_mismatch,
    NOT registry.production_type_species_valid
        AS production_type_species_mismatch
FROM livestock_registry_entries registry;

COMMENT ON VIEW livestock_registry_validation IS
    'Release-scoped ET-LITS registry rows whose breed or production type does not agree with the national reference data';

COMMIT;
