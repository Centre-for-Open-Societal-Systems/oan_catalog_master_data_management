BEGIN;

CREATE TABLE g2p_seed_variety_source_record (
    source_variety_id       INTEGER PRIMARY KEY,
    seed_crop_id            INTEGER NOT NULL REFERENCES g2p_seed_catalog(id),
    crop_name_raw           TEXT NOT NULL,
    common_name_raw         TEXT NOT NULL,
    category_raw            TEXT,
    release_year            SMALLINT,
    release_date            DATE,
    release_raw             TEXT,
    maintainer              TEXT,
    source_classification   VARCHAR,
    details_url             TEXT NOT NULL UNIQUE,
    matched_variety_code    VARCHAR REFERENCES g2p_crop_variety(variety_code),
    match_method            VARCHAR NOT NULL DEFAULT 'UNRESOLVED',
    match_status            VARCHAR NOT NULL DEFAULT 'UNRESOLVED',
    review_note             TEXT,
    CONSTRAINT ck_g2p_seed_variety_source_id
        CHECK (source_variety_id > 0),
    CONSTRAINT ck_g2p_seed_variety_release_year
        CHECK (release_year IS NULL OR release_year BETWEEN 1800 AND 2200),
    CONSTRAINT ck_g2p_seed_variety_release_date_year
        CHECK (release_year IS NULL OR release_date IS NULL
               OR EXTRACT(YEAR FROM release_date) = release_year),
    CONSTRAINT ck_g2p_seed_variety_source_classification
        CHECK (source_classification IS NULL
               OR source_classification IN ('Domestic', 'Imported')),
    CONSTRAINT ck_g2p_seed_variety_match_state
        CHECK (
            (match_status = 'MATCHED'
             AND matched_variety_code IS NOT NULL
             AND match_method IN (
                 'EXACT_SOURCE_ID', 'EXACT_NAME_AND_CROP',
                 'REVIEWED_ALIAS', 'REVIEWED_MANUAL'
             ))
            OR
            (match_status = 'UNRESOLVED'
             AND matched_variety_code IS NULL
             AND match_method = 'UNRESOLVED')
            OR
            (match_status = 'CONFLICT'
             AND matched_variety_code IS NULL
             AND match_method = 'CONFLICT')
        )
);

CREATE INDEX ix_g2p_seed_variety_seed_crop
    ON g2p_seed_variety_source_record (seed_crop_id);
CREATE INDEX ix_g2p_seed_variety_match
    ON g2p_seed_variety_source_record (match_status, matched_variety_code);
CREATE INDEX ix_g2p_seed_variety_release_year
    ON g2p_seed_variety_source_record (release_year);

CREATE TABLE seed_variety_source_records (
    seed_variety_source_record_id VARCHAR PRIMARY KEY,
    release_id                   VARCHAR NOT NULL
                                 REFERENCES catalogue_releases(release_id) ON DELETE CASCADE,
    seed_variety_value_id        VARCHAR NOT NULL
                                 REFERENCES catalogue_values(catalogue_value_id) ON DELETE CASCADE,
    seed_crop_value_id           VARCHAR NOT NULL
                                 REFERENCES catalogue_values(catalogue_value_id) ON DELETE CASCADE,
    matched_crop_variety_value_id VARCHAR
                                  REFERENCES catalogue_values(catalogue_value_id) ON DELETE CASCADE,
    source_variety_id            INTEGER NOT NULL,
    crop_name_raw                TEXT NOT NULL,
    common_name_raw              TEXT NOT NULL,
    category_raw                 TEXT,
    release_year                 SMALLINT,
    release_date                 DATE,
    release_raw                  TEXT,
    maintainer                   TEXT,
    source_classification        VARCHAR,
    details_url                  TEXT NOT NULL,
    match_method                 VARCHAR NOT NULL,
    match_status                 VARCHAR NOT NULL,
    review_note                  TEXT,
    CONSTRAINT uq_seed_variety_source_release_id
        UNIQUE (release_id, source_variety_id),
    CONSTRAINT uq_seed_variety_source_release_url
        UNIQUE (release_id, details_url),
    CONSTRAINT ck_seed_variety_source_id
        CHECK (source_variety_id > 0),
    CONSTRAINT ck_seed_variety_source_release_year
        CHECK (release_year IS NULL OR release_year BETWEEN 1800 AND 2200),
    CONSTRAINT ck_seed_variety_source_release_date_year
        CHECK (release_year IS NULL OR release_date IS NULL
               OR EXTRACT(YEAR FROM release_date) = release_year),
    CONSTRAINT ck_seed_variety_source_classification
        CHECK (source_classification IS NULL
               OR source_classification IN ('Domestic', 'Imported')),
    CONSTRAINT ck_seed_variety_source_match_state
        CHECK (
            (match_status = 'MATCHED'
             AND matched_crop_variety_value_id IS NOT NULL
             AND match_method IN (
                 'EXACT_SOURCE_ID', 'EXACT_NAME_AND_CROP',
                 'REVIEWED_ALIAS', 'REVIEWED_MANUAL'
             ))
            OR
            (match_status = 'UNRESOLVED'
             AND matched_crop_variety_value_id IS NULL
             AND match_method = 'UNRESOLVED')
            OR
            (match_status = 'CONFLICT'
             AND matched_crop_variety_value_id IS NULL
             AND match_method = 'CONFLICT')
        )
);

CREATE INDEX ix_seed_variety_source_release_crop
    ON seed_variety_source_records (release_id, seed_crop_value_id);
CREATE INDEX ix_seed_variety_source_release_value
    ON seed_variety_source_records (release_id, seed_variety_value_id);
CREATE INDEX ix_seed_variety_source_release_match
    ON seed_variety_source_records
       (release_id, match_status, matched_crop_variety_value_id);
CREATE INDEX ix_seed_variety_source_release_year
    ON seed_variety_source_records (release_id, release_year);

COMMIT;
