/**
 * Queries behind the catalogue dashboard.
 *
 * These are the catalog panels of the OAN dashboard re-pointed at this repo's
 * schema: the `g2p_*` staging tables the seed loads, which are the raw
 * reference data the API projects its releases from. The dashboard the panels
 * came from read equivalent tables under different names (`crop_catalog`,
 * `eth_regions`, ...), so the figures are this catalogue's own, not that
 * dashboard's.
 *
 * Every query is national and takes no parameters — reference data is not
 * scoped by geography — so they are executed as literal SQL with no user
 * input interpolated.
 *
 * The one panel row that has no equivalent here is the farmer registry: this
 * database holds no farmer records, so that slot reports the service's own
 * published release (catalogues, values, relations, geography) instead.
 */
export const CHART_QUERIES: Record<string, string> = {
  catalogKpis: `
    SELECT
      (SELECT COUNT(*) FROM g2p_crop) AS crops,
      (SELECT COUNT(*) FROM g2p_crop_variety) AS varieties,
      (SELECT COUNT(*) FROM g2p_crop_category) AS crop_categories,
      (SELECT COUNT(*) FROM g2p_ecological_zone) AS ecological_zones,
      (SELECT COUNT(*) FROM g2p_seed_catalog) AS seed_crops,
      (SELECT COUNT(DISTINCT budget_year) FROM g2p_seed_demand_trend) AS seed_years,
      (SELECT COALESCE(SUM(quantity_demanded), 0) FROM g2p_seed_demand_trend) AS seed_demand_quantity,
      (SELECT COUNT(*) FROM g2p_livestock_type) AS species,
      (SELECT COUNT(*) FROM g2p_livestock_breed) AS breeds,
      (SELECT COUNT(*) FROM g2p_livestock_registry_entry) AS livestock_records,
      (SELECT COUNT(*) FROM g2p_region) AS regions,
      (SELECT COUNT(*) FROM g2p_zone) AS zones,
      (SELECT COUNT(*) FROM g2p_woreda) AS woredas
  `,

  // One row per connected registry. "Connected" means the tables backing that
  // registry are present and populated; faults are live referential checks.
  catalogRegistrySources: `
    SELECT
      1 AS sort_order,
      'crop' AS registry_key,
      'Crop Catalog' AS registry,
      'Ethio-Seed (MOA)' AS upstream,
      (SELECT COUNT(*) FROM g2p_crop)
        + (SELECT COUNT(*) FROM g2p_crop_variety)
        + (SELECT COUNT(*) FROM g2p_crop_category)
        + (SELECT COUNT(*) FROM g2p_ecological_zone) AS records,
      (SELECT COUNT(*) FROM g2p_crop WHERE category_id IS NULL)
        + (SELECT COUNT(*) FROM g2p_crop WHERE preferred_ecological_zone_id IS NULL)
        + (SELECT COUNT(*) FROM g2p_crop_variety v
            WHERE NOT EXISTS (SELECT 1 FROM g2p_crop_variety_source_record r
                               WHERE r.variety_code = v.variety_code
                                 AND r.release_year IS NOT NULL)) AS faults,
      (SELECT COUNT(*) FROM g2p_crop)::text || ' crops · '
        || (SELECT COUNT(*) FROM g2p_crop_variety)::text || ' varieties' AS detail
    UNION ALL
    SELECT
      2,
      'seed',
      'Seed Catalog',
      'Ethio-Seed demand (MOA)',
      (SELECT COUNT(*) FROM g2p_seed_catalog)
        + (SELECT COUNT(*) FROM g2p_seed_demand_trend)
        + (SELECT COUNT(*) FROM g2p_seed_demand_trend_by_crop)
        + (SELECT COUNT(*) FROM g2p_seed_demand_summary),
      (SELECT COUNT(*) FROM g2p_seed_catalog s
        WHERE NOT EXISTS (SELECT 1 FROM g2p_seed_demand_trend_by_crop d WHERE d.crop_id = s.id)),
      (SELECT COUNT(*) FROM g2p_seed_catalog)::text || ' crops · '
        || (SELECT COUNT(DISTINCT budget_year) FROM g2p_seed_demand_trend)::text || ' budget years'
    UNION ALL
    SELECT
      3,
      'livestock',
      'Livestock Catalog',
      'LIS (MOA)',
      (SELECT COUNT(*) FROM g2p_livestock_type)
        + (SELECT COUNT(*) FROM g2p_livestock_breed)
        + (SELECT COUNT(*) FROM g2p_livestock_population),
      (SELECT COUNT(*) FROM g2p_livestock_type WHERE in_etlits_registry AND NOT in_lis_population)
        + (SELECT COUNT(*) FROM g2p_livestock_breed WHERE NOT in_national_standard),
      (SELECT COUNT(*) FROM g2p_livestock_type)::text || ' species · '
        || (SELECT COUNT(*) FROM g2p_livestock_breed)::text || ' breeds'
    UNION ALL
    SELECT
      4,
      'etlits',
      'Livestock Registry',
      'ET-LITS (MOA)',
      (SELECT COUNT(*) FROM g2p_livestock_registry_entry),
      (SELECT COUNT(*) FROM g2p_livestock_registry_entry WHERE breed_id IS NULL)
        + (SELECT COUNT(*) FROM g2p_livestock_registry_entry e
             JOIN g2p_livestock_breed b ON b.id = e.breed_id
             JOIN g2p_livestock_type t ON t.id = b.species_id
            WHERE t.species_code <> e.species_code)
        + (SELECT COUNT(*) FROM g2p_livestock_registry_entry e
            WHERE NOT EXISTS (SELECT 1 FROM g2p_livestock_production_type_species s
                                JOIN g2p_livestock_type t ON t.id = s.species_id
                               WHERE t.species_code = e.species_code
                                 AND s.production_type_code = e.production_type_code)),
      (SELECT COUNT(*) FROM g2p_livestock_registry_entry WHERE status = 'ACTIVE')::text
        || ' active of ' || (SELECT COUNT(*) FROM g2p_livestock_registry_entry)::text || ' records'
    UNION ALL
    SELECT
      5,
      'location',
      'Location Catalog',
      'OCHA / HDX 2021',
      (SELECT COUNT(*) FROM g2p_region)
        + (SELECT COUNT(*) FROM g2p_zone)
        + (SELECT COUNT(*) FROM g2p_woreda),
      (SELECT COUNT(*) FROM g2p_zone z
        WHERE NOT EXISTS (SELECT 1 FROM g2p_region r WHERE r.id = z.region))
        + (SELECT COUNT(*) FROM g2p_woreda w
            WHERE NOT EXISTS (SELECT 1 FROM g2p_zone z WHERE z.id = w.zone)),
      (SELECT COUNT(*) FROM g2p_region)::text || ' regions · '
        || (SELECT COUNT(*) FROM g2p_woreda)::text || ' woredas'
    UNION ALL
    SELECT
      6,
      'catalogue',
      'Catalogue Release',
      'catalogue-service',
      (SELECT COUNT(*) FROM catalogue_values)
        + (SELECT COUNT(*) FROM catalogue_value_relations)
        + (SELECT COUNT(*) FROM geography_units),
      (SELECT COUNT(*) FROM catalogue_values v
        WHERE v.parent_value_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM catalogue_values p WHERE p.catalogue_value_id = v.parent_value_id))
        + (SELECT COUNT(*) FROM catalogue_value_relations r
            WHERE NOT EXISTS (SELECT 1 FROM catalogue_values v WHERE v.catalogue_value_id = r.source_value_id)
               OR NOT EXISTS (SELECT 1 FROM catalogue_values v WHERE v.catalogue_value_id = r.target_value_id))
        + (SELECT COUNT(*) FROM geography_units u
            WHERE u.parent_unit_id IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM geography_units p WHERE p.geography_unit_id = u.parent_unit_id)),
      (SELECT COUNT(*) FROM catalogues)::text || ' catalogues · '
        || (SELECT COUNT(*) FROM catalogue_values)::text || ' values'
    ORDER BY sort_order
  `,

  // Live referential checks across the catalogs, one row per check.
  catalogIntegrationFaults: `
    SELECT 'Livestock Registry' AS source, 'Breed not resolved to the standard' AS fault,
           'danger' AS severity, COUNT(*) AS records
      FROM g2p_livestock_registry_entry WHERE breed_id IS NULL
    UNION ALL
    SELECT 'Livestock Registry', 'Breed does not match the record species', 'danger', COUNT(*)
      FROM g2p_livestock_registry_entry e
      JOIN g2p_livestock_breed b ON b.id = e.breed_id
      JOIN g2p_livestock_type t ON t.id = b.species_id
     WHERE t.species_code <> e.species_code
    UNION ALL
    SELECT 'Livestock Registry', 'Production type invalid for species', 'danger', COUNT(*)
      FROM g2p_livestock_registry_entry e
     WHERE NOT EXISTS (SELECT 1 FROM g2p_livestock_production_type_species s
                         JOIN g2p_livestock_type t ON t.id = s.species_id
                        WHERE t.species_code = e.species_code
                          AND s.production_type_code = e.production_type_code)
    UNION ALL
    SELECT 'Location Catalog', 'Admin units with an unknown parent', 'danger',
           (SELECT COUNT(*) FROM g2p_zone z
             WHERE NOT EXISTS (SELECT 1 FROM g2p_region r WHERE r.id = z.region))
         + (SELECT COUNT(*) FROM g2p_woreda w
             WHERE NOT EXISTS (SELECT 1 FROM g2p_zone z WHERE z.id = w.zone))
    UNION ALL
    SELECT 'Catalogue Release', 'Values with an unresolved parent', 'danger', COUNT(*)
      FROM catalogue_values v
     WHERE v.parent_value_id IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM catalogue_values p WHERE p.catalogue_value_id = v.parent_value_id)
    UNION ALL
    SELECT 'Catalogue Release', 'Relations pointing at a missing value', 'danger', COUNT(*)
      FROM catalogue_value_relations r
     WHERE NOT EXISTS (SELECT 1 FROM catalogue_values v WHERE v.catalogue_value_id = r.source_value_id)
        OR NOT EXISTS (SELECT 1 FROM catalogue_values v WHERE v.catalogue_value_id = r.target_value_id)
    UNION ALL
    SELECT 'Crop Catalog', 'Crops with no category assigned', 'warning', COUNT(*)
      FROM g2p_crop WHERE category_id IS NULL
    UNION ALL
    SELECT 'Crop Catalog', 'Crops with no ecological zone', 'warning', COUNT(*)
      FROM g2p_crop WHERE preferred_ecological_zone_id IS NULL
    UNION ALL
    SELECT 'Crop Catalog', 'Varieties with no release year', 'warning', COUNT(*)
      FROM g2p_crop_variety v
     WHERE NOT EXISTS (SELECT 1 FROM g2p_crop_variety_source_record r
                        WHERE r.variety_code = v.variety_code AND r.release_year IS NOT NULL)
    UNION ALL
    SELECT 'Seed Catalog', 'Catalogued crops with no demand record', 'info', COUNT(*)
      FROM g2p_seed_catalog s
     WHERE NOT EXISTS (SELECT 1 FROM g2p_seed_demand_trend_by_crop d WHERE d.crop_id = s.id)
    UNION ALL
    SELECT 'Livestock Catalog', 'Species in ET-LITS but absent from LIS population', 'info', COUNT(*)
      FROM g2p_livestock_type WHERE in_etlits_registry AND NOT in_lis_population
    UNION ALL
    SELECT 'Livestock Catalog', 'Breeds outside the national standard', 'info', COUNT(*)
      FROM g2p_livestock_breed WHERE NOT in_national_standard
    ORDER BY records DESC
  `,

  // Upstream systems the catalogs are sourced from, derived from the source
  // and URL columns carried on the catalog records themselves.
  catalogExternalIntegrations: `
    SELECT
      1 AS sort_order,
      'Ethio-Seed Variety Service' AS system,
      'ethioseed.moa.gov.et' AS endpoint,
      'Crop varieties' AS domain,
      COUNT(*) FILTER (WHERE has_url) AS linked_records,
      COUNT(*) FILTER (WHERE NOT has_url) AS faults
    FROM (
      SELECT EXISTS (SELECT 1 FROM g2p_crop_variety_source_record r
                      WHERE r.variety_code = v.variety_code AND r.source_url IS NOT NULL) AS has_url
        FROM g2p_crop_variety v
    ) variety_urls
    UNION ALL
    SELECT
      2,
      'LIS Species Reference',
      'lis.moa.gov.et',
      'Livestock species',
      COUNT(*) FILTER (WHERE icon_url IS NOT NULL),
      COUNT(*) FILTER (WHERE icon_url IS NULL)
    FROM g2p_livestock_type
    UNION ALL
    SELECT
      3,
      'ET-LITS Registry Feed',
      'et-lits.moa.gov.et',
      'Livestock records',
      (SELECT COUNT(*) FROM g2p_livestock_registry_entry),
      (SELECT COUNT(*) FROM g2p_livestock_registry_entry WHERE breed_id IS NULL)
    UNION ALL
    SELECT
      4,
      'National Livestock Data Standard',
      'MOA standard (2024)',
      'Breed reference',
      COUNT(*) FILTER (WHERE in_national_standard),
      COUNT(*) FILTER (WHERE NOT in_national_standard)
    FROM g2p_livestock_breed
    UNION ALL
    SELECT
      5,
      'OCHA / HDX Boundaries',
      'data.humdata.org',
      'Admin boundaries',
      (SELECT COUNT(*) FROM g2p_region)
        + (SELECT COUNT(*) FROM g2p_zone)
        + (SELECT COUNT(*) FROM g2p_woreda),
      (SELECT COUNT(*) FROM g2p_zone z
        WHERE NOT EXISTS (SELECT 1 FROM g2p_region r WHERE r.id = z.region))
        + (SELECT COUNT(*) FROM g2p_woreda w
            WHERE NOT EXISTS (SELECT 1 FROM g2p_zone z WHERE z.id = w.zone))
    ORDER BY sort_order
  `,

  catalogCropsByCategory: `
    SELECT
      COALESCE(cc.name, 'Uncategorised') AS category,
      COUNT(c.id) AS crops
    FROM g2p_crop c
    LEFT JOIN g2p_crop_category cc ON cc.id = c.category_id
    GROUP BY 1
    ORDER BY crops DESC
  `,

  // Varieties are counted per taxonomy type first: several catalogue crops can
  // share one type, and counting after that join would double them.
  catalogTopCropsByVariety: `
    SELECT
      COALESCE(crop.name, t.display_name, v.type_code) AS crop,
      v.varieties
    FROM (
      SELECT type_code, COUNT(*) AS varieties
        FROM g2p_crop_variety
       GROUP BY type_code
    ) v
    LEFT JOIN g2p_crop_taxonomy_type t ON t.type_code = v.type_code
    LEFT JOIN LATERAL (
      SELECT c.name FROM g2p_crop c WHERE c.taxonomy_type_code = v.type_code ORDER BY c.id LIMIT 1
    ) crop ON TRUE
    ORDER BY v.varieties DESC
    LIMIT 8
  `,

  // Release years live on the source records the varieties were matched from.
  catalogVarietyTimeline: `
    SELECT
      release_year::text AS year,
      COUNT(DISTINCT variety_code) AS varieties
    FROM g2p_crop_variety_source_record
    WHERE release_year BETWEEN 1950 AND 2100
    GROUP BY 1
    ORDER BY 1
  `,

  catalogVarietySource: `
    SELECT
      COALESCE(NULLIF(TRIM(source_classification), ''), 'Unknown') AS source,
      COUNT(*) AS varieties
    FROM g2p_seed_variety_source_record
    GROUP BY 1
    ORDER BY varieties DESC
  `,

  catalogBreedsBySpecies: `
    SELECT
      t.name AS species,
      b.breed_type,
      COUNT(*) AS breeds
    FROM g2p_livestock_breed b
    JOIN g2p_livestock_type t ON t.id = b.species_id
    GROUP BY 1, 2
    ORDER BY 1, 2
  `,

  catalogSeedDemandByClass: `
    SELECT
      budget_year,
      seed_class,
      quantity_demanded
    FROM g2p_seed_demand_trend
    ORDER BY budget_year, seed_class
  `,

  catalogSeedDemandByCrop: `
    SELECT
      crop_name,
      SUM(quantity_demanded) AS quantity
    FROM g2p_seed_demand_trend_by_crop
    GROUP BY 1
    ORDER BY quantity DESC
    LIMIT 6
  `,

  // Walked through the zone table: woredas carry a zone, not a region.
  catalogLocationHierarchy: `
    SELECT
      r.name AS region,
      r.admin1_pcod AS region_pcode,
      (SELECT COUNT(*) FROM g2p_zone z WHERE z.region = r.id) AS zones,
      (SELECT COUNT(*) FROM g2p_woreda w
         JOIN g2p_zone z ON z.id = w.zone
        WHERE z.region = r.id) AS woredas
    FROM g2p_region r
    ORDER BY woredas DESC
  `,

  catalogLivestockRegistryStatus: `
    SELECT
      s.code AS status,
      s.name,
      s.sort_order,
      s.is_live_master_data,
      COUNT(e.id) AS records
    FROM g2p_livestock_record_status s
    LEFT JOIN g2p_livestock_registry_entry e ON e.status = s.code
    GROUP BY 1, 2, 3, 4
    ORDER BY s.sort_order
  `,
};

export type ChartName = keyof typeof CHART_QUERIES;
