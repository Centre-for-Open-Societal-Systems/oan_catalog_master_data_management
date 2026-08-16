BEGIN;

CREATE TABLE IF NOT EXISTS g2p_crop_category (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS g2p_ecological_zone (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR NOT NULL,
    description TEXT
);

CREATE TABLE IF NOT EXISTS catalogue_value_relations (
    relation_id     VARCHAR PRIMARY KEY,
    source_value_id VARCHAR NOT NULL
                    REFERENCES catalogue_values(catalogue_value_id) ON DELETE CASCADE,
    relation_type   VARCHAR NOT NULL,
    target_value_id VARCHAR NOT NULL
                    REFERENCES catalogue_values(catalogue_value_id) ON DELETE CASCADE,
    CONSTRAINT uq_catalogue_value_relation
        UNIQUE (source_value_id, relation_type, target_value_id),
    CONSTRAINT ck_catalogue_value_relation_not_self
        CHECK (source_value_id <> target_value_id)
);

CREATE INDEX IF NOT EXISTS ix_catalogue_value_relation_source
    ON catalogue_value_relations (source_value_id);
CREATE INDEX IF NOT EXISTS ix_catalogue_value_relation_target
    ON catalogue_value_relations (target_value_id);
CREATE INDEX IF NOT EXISTS ix_catalogue_value_relation_type
    ON catalogue_value_relations (relation_type);

COMMIT;
