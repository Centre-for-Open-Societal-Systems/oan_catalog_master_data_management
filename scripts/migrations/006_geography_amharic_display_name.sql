BEGIN;

ALTER TABLE g2p_region
    ADD COLUMN IF NOT EXISTS display_name_amh VARCHAR;

ALTER TABLE g2p_zone
    ADD COLUMN IF NOT EXISTS display_name_amh VARCHAR;

ALTER TABLE g2p_woreda
    ADD COLUMN IF NOT EXISTS display_name_amh VARCHAR;

ALTER TABLE geography_units
    ADD COLUMN IF NOT EXISTS display_name_amh VARCHAR;

COMMIT;
