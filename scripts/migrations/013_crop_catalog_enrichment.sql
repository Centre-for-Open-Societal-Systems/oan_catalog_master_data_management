BEGIN;

ALTER TABLE g2p_crop
    ADD COLUMN scientific_name VARCHAR,
    ADD COLUMN centre VARCHAR,
    ADD COLUMN varieties_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN image_url VARCHAR,
    ADD COLUMN display_name_amh VARCHAR,
    ADD COLUMN taxonomy_type_code VARCHAR,
    ADD COLUMN taxonomy_source_id VARCHAR,
    ADD COLUMN taxonomy_category_code VARCHAR,
    ADD COLUMN taxonomy_description TEXT,
    ADD COLUMN record_source VARCHAR NOT NULL DEFAULT 'SQL_CROP_CATALOG',
    ADD COLUMN varieties_count_source VARCHAR NOT NULL DEFAULT 'SQL_CROP_VARIETY',
    ADD COLUMN taxonomy_match_method VARCHAR NOT NULL DEFAULT 'UNRESOLVED',
    ADD COLUMN taxonomy_match_status VARCHAR NOT NULL DEFAULT 'UNRESOLVED',
    ADD CONSTRAINT ck_g2p_crop_varieties_count_nonnegative
        CHECK (varieties_count >= 0);

COMMENT ON COLUMN g2p_crop.varieties_count IS
    'Computed from crop-variety source rows; not copied from workbook varietiesCount';
COMMENT ON COLUMN g2p_crop.taxonomy_source_id IS
    'Workbook cropTypeId retained for source traceability';

COMMIT;
