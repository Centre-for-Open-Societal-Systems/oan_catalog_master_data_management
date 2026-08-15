BEGIN;

CREATE TABLE g2p_kebele (
    code                  VARCHAR PRIMARY KEY,
    display_name          TEXT NOT NULL,
    display_name_amh      TEXT,
    source_code           VARCHAR NOT NULL UNIQUE,
    source_region_code    VARCHAR,
    source_zone_code      VARCHAR,
    source_woreda_code    VARCHAR,
    matched_woreda_code   VARCHAR REFERENCES g2p_woreda(code),
    match_method          VARCHAR NOT NULL,
    match_status          VARCHAR NOT NULL,
    review_note           TEXT,
    CONSTRAINT ck_g2p_kebele_code CHECK (code ~ '^ET[0-9]{12}$'),
    CONSTRAINT ck_g2p_kebele_match_state CHECK (
        (match_status = 'MATCHED'
         AND matched_woreda_code IS NOT NULL
         AND match_method IN (
             'EXACT_WOREDA_CODE', 'WOREDA_REFERENCE',
             'REVIEWED_CODE_HIERARCHY', 'REVIEWED_CROSSWALK'
         ))
        OR
        (match_status = 'UNRESOLVED'
         AND matched_woreda_code IS NULL
         AND match_method = 'UNRESOLVED')
    )
);

CREATE INDEX ix_g2p_kebele_parent
    ON g2p_kebele (matched_woreda_code);
CREATE INDEX ix_g2p_kebele_match
    ON g2p_kebele (match_status, match_method);

COMMIT;
