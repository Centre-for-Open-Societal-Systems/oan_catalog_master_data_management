export type ReleaseData = {
  country_code: string;
  version: string;
  schema_version: string;
  checksum: string;
  source: string;
  status: "ACTIVE" | "RETIRED";
  activated_at: string;
};

export type CatalogueData = {
  code: string;
  domain: string | null;
  display_name: string;
  display_name_i18n: Record<string, string> | null;
  is_hierarchical: boolean;
  status: string;
};

export type CatalogueValueRelation = {
  type: string;
  target_catalogue_code: string;
  target_code: string;
  target_display_name: string;
};

export type CatalogueValueData = {
  code: string;
  parent_code: string | null;
  display_name: string;
  display_name_i18n: Record<string, string> | null;
  semantic_roles: string[];
  sort_order: number | null;
  valid_from: string | null;
  valid_to: string | null;
  status: string;
  metadata: Record<string, unknown>;
  relations: CatalogueValueRelation[];
};

export type GeographyLevelData = {
  code: string;
  display_name: string;
  display_name_i18n: Record<string, string> | null;
  level_order: number;
  parent_level_code: string | null;
};

export type GeographyUnitData = {
  code: string;
  level_code: string;
  parent_code: string | null;
  display_name: string;
  display_name_amh: string | null;
  display_name_i18n: Record<string, string> | null;
  latitude: string | null;
  longitude: string | null;
  valid_from: string | null;
  valid_to: string | null;
  status: string;
  aliases: string[];
  metadata: Record<string, unknown>;
};

export type LivestockPopulationStat = {
  species_code: string;
  census_year: number;
  population_total: number;
  source_record_count: number;
  source: string;
};

export type SeedDemandSummaryStat = {
  budget_year: number;
  total_entries: number;
  total_quantity_demanded: string;
  average_quantity_per_entry: string;
  total_estimated_land_ha: string;
  average_estimated_land_ha: string;
};

export type SeedDemandTrendStat = {
  budget_year: number;
  seed_class: string;
  quantity_demanded: string;
};

export type SeedDemandByCropStat = {
  crop_code: string;
  crop_name: string;
  budget_year: number;
  seed_class: string;
  quantity_demanded: string;
};

export type Paged<T> = {
  release: ReleaseData;
  total: number;
  page: number;
  page_size: number;
} & T;

export type HealthReady = {
  status: "ready" | "not_ready";
  checks: { database: "up" | "down"; schema: "current" | "mismatch" | "unknown" };
  schema_version: string;
  expected_schema_version: string;
};

export type CropTaxonomyReference = {
  code: string;
  display_name: string;
  display_name_i18n: Record<string, string> | null;
};

export type CropVarietyCharacteristic = {
  code: string;
  display_name: string;
  value_type: string;
  raw_value: string;
  value_text: string | null;
  value_numeric: string | null;
  value_boolean: boolean | null;
  value_min: string | null;
  value_max: string | null;
  unit_code: string | null;
};

export type CropVarietySourceRecord = {
  source_record_code: string;
  source_row_number: number | null;
  centre: string;
  release_year_raw: string;
  release_year: number | null;
  source_url: string | null;
  altitude_min_m: string | null;
  altitude_max_m: string | null;
  rainfall_min_mm: string | null;
  rainfall_max_mm: string | null;
  days_to_maturity_min: number | null;
  days_to_maturity_max: number | null;
  yield_research_min_qt_ha: string | null;
  yield_research_max_qt_ha: string | null;
  yield_farmer_min_qt_ha: string | null;
  yield_farmer_max_qt_ha: string | null;
  seed_rate_kg_ha: string | null;
  adaptation_area: string | null;
  planting_date_text: string | null;
  crop_pest_reaction: string | null;
  characteristics: CropVarietyCharacteristic[];
};

export type CropVarietyDetail = {
  code: string;
  display_name: string;
  display_name_i18n: Record<string, string> | null;
  status: string;
  crop_type: CropTaxonomyReference;
  category: CropTaxonomyReference;
  source_records: CropVarietySourceRecord[];
};

export type MatchStatus = "MATCHED" | "UNRESOLVED" | "CONFLICT";

export type SeedVarietyData = {
  code: string;
  display_name: string;
  status: string;
  source_variety_id: number;
  seed_crop: CropTaxonomyReference;
  matched_crop_variety: CropTaxonomyReference | null;
  crop_type: CropTaxonomyReference | null;
  category: CropTaxonomyReference | null;
  crop_name_raw: string;
  common_name_raw: string;
  category_raw: string | null;
  release_year: number | null;
  release_date: string | null;
  release_raw: string | null;
  maintainer: string | null;
  source_classification: string | null;
  details_url: string;
  match_method: string;
  match_status: MatchStatus;
  review_note: string | null;
};

export type LivestockReference = { code: string; display_name: string };

export type LivestockSpecies = {
  code: string;
  display_name: string;
  status: string;
  description: string | null;
  icon_url: string | null;
  dataset_id: number | null;
  scientific_name: string | null;
  subfamily: string | null;
  species_type_code: number | null;
  chart_color: string | null;
  ear_tag_range: string | null;
  in_lis_population: boolean;
  in_etlits_registry: boolean;
};

export type LivestockBreedType = "Indigenous" | "Exotic" | "Cross";

export type LivestockBreed = {
  code: string;
  display_name: string;
  status: string;
  species: LivestockReference;
  source_id: number;
  breed_code: string | null;
  abbreviation: string | null;
  breed_type: LivestockBreedType;
  in_national_standard: boolean;
  in_etlits_registry: boolean;
  source: string;
};

export type LivestockGender = {
  code: string;
  display_name: string;
  description: string | null;
  in_etlits_registry: boolean;
};

export type LivestockLocationType = {
  code: string;
  display_name: string;
  ethiopian_zone_name: string | null;
  altitude_description: string | null;
  description: string | null;
  ecological_zone: LivestockReference;
};

export type LivestockBodyCondition = {
  code: string;
  display_name: string;
  bcs_score: number;
  condition_label: string;
  fatness_label: string;
  etlits_label: string | null;
  description: string | null;
};

export type LivestockProductionType = {
  code: string;
  display_name: string;
  standard_purpose: string | null;
  in_national_standard: boolean;
  in_etlits_registry: boolean;
  description: string | null;
  valid_species: LivestockReference[];
};

export type LivestockRecordStatus = {
  code: string;
  display_name: string;
  sort_order: number;
  is_live_master_data: boolean;
  description: string | null;
};

export type LivestockReferenceDataBundle = {
  genders: LivestockGender[];
  location_types: LivestockLocationType[];
  body_conditions: LivestockBodyCondition[];
  production_types: LivestockProductionType[];
  record_statuses: LivestockRecordStatus[];
};

export type LivestockRegistryValidation = {
  id: string;
  status: string;
  species_code: string;
  breed_name: string;
  breed_code: string | null;
  breed_species_code: string | null;
  production_type_code: string;
  breed_unrecognised: boolean;
  breed_outside_national_standard: boolean;
  breed_species_mismatch: boolean;
  production_type_species_mismatch: boolean;
};

export type LivestockRegistryEntry = {
  id: string;
  species_code: string;
  breed_name: string;
  breed_id: number | null;
  breed_code: string | null;
  breed_species_code: string | null;
  gender_code: string;
  location_type_code: string;
  body_condition_code: string;
  production_type_code: string;
  status: string;
  created_on: string;
  updated_on: string;
  validation: LivestockRegistryValidation;
};
