BEGIN;

-- Preserve the source SQL hierarchy explicitly.  The source column called
-- crop_id was previously stored only as seed_crop_id; both identifiers have
-- the same value today, but only seed_crop_id had a foreign key.
ALTER TABLE g2p_seed_variety_source_record
    ADD COLUMN crop_id INTEGER GENERATED ALWAYS AS (seed_crop_id) STORED NOT NULL,
    ADD CONSTRAINT fk_g2p_seed_variety_crop
        FOREIGN KEY (crop_id) REFERENCES g2p_crop(id);

CREATE INDEX ix_g2p_seed_variety_crop
    ON g2p_seed_variety_source_record (crop_id);

-- Release-scoped source records retain both the compatibility seed catalogue
-- reference and the direct consolidated crop/crop-variety references.
ALTER TABLE seed_variety_source_records
    ADD COLUMN crop_value_id VARCHAR
        REFERENCES catalogue_values(catalogue_value_id) ON DELETE CASCADE,
    ADD COLUMN consolidated_crop_variety_value_id VARCHAR
        REFERENCES catalogue_values(catalogue_value_id) ON DELETE CASCADE;

CREATE INDEX ix_seed_variety_source_release_consolidated_crop
    ON seed_variety_source_records (release_id, crop_value_id);
CREATE INDEX ix_seed_variety_source_release_consolidated_variety
    ON seed_variety_source_records
       (release_id, consolidated_crop_variety_value_id);

-- Record whether the consolidated crop category came directly from the SQL
-- source or was filled through the reviewed workbook-to-SQL category map.
ALTER TABLE g2p_crop
    ADD COLUMN category_source VARCHAR NOT NULL DEFAULT 'UNRESOLVED',
    ADD CONSTRAINT ck_g2p_crop_category_source
        CHECK (category_source IN (
            'SQL_CROP_CATALOG', 'WORKBOOK_TAXONOMY_MAPPING', 'UNRESOLVED'
        ));

COMMIT;
