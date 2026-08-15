import type {
  CatalogueData,
  CatalogueValueData,
  CropVarietyDetail,
  GeographyLevelData,
  GeographyUnitData,
  HealthReady,
  LivestockBreed,
  LivestockBreedType,
  LivestockPopulationStat,
  LivestockReferenceDataBundle,
  LivestockRegistryEntry,
  LivestockRegistryValidation,
  LivestockSpecies,
  MatchStatus,
  Paged,
  ReleaseData,
  SeedDemandByCropStat,
  SeedDemandSummaryStat,
  SeedDemandTrendStat,
  SeedVarietyData,
} from "./types";

const BASE_URL = process.env.CATALOGUE_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(path, BASE_URL);
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  }

  let res: Response;
  try {
    res = await fetch(url, { cache: "no-store" });
  } catch {
    throw new Error(
      `Could not reach catalogue-api at ${BASE_URL}. Is it running? (docker compose up in catalogue-service/)`
    );
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${path} -> ${res.status} ${res.statusText}${body ? `: ${body}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export function getCurrentRelease(releaseVersion?: string) {
  return apiFetch<ReleaseData>("/v1/releases/current", { release_version: releaseVersion });
}

export function getCatalogues(domain?: string) {
  return apiFetch<{ release: ReleaseData; catalogues: CatalogueData[] }>("/v1/catalogues", { domain });
}

export function getCatalogueValues(
  catalogueCode: string,
  opts: {
    status?: string;
    parent_code?: string;
    relation_type?: string;
    related_catalogue_code?: string;
    related_value_code?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}
) {
  return apiFetch<Paged<{ catalogue: CatalogueData; values: CatalogueValueData[] }>>(
    `/v1/catalogues/${encodeURIComponent(catalogueCode)}/values`,
    { page_size: 25, ...opts }
  );
}

export function getGeographyLevels() {
  return apiFetch<{ release: ReleaseData; levels: GeographyLevelData[] }>("/v1/geography/levels");
}

export function getGeographyUnits(opts: { level_code?: string; parent_code?: string; status?: string; search?: string; page?: number; page_size?: number } = {}) {
  return apiFetch<Paged<{ units: GeographyUnitData[] }>>("/v1/geography/units", { page_size: 25, ...opts });
}

export function getGeographyUnit(unitCode: string, levelCode?: string) {
  return apiFetch<{ release: ReleaseData; unit: GeographyUnitData }>(
    `/v1/geography/units/${encodeURIComponent(unitCode)}`,
    { level_code: levelCode }
  );
}

export function getLivestockPopulation(opts: { species_code?: string; census_year?: number; page?: number; page_size?: number } = {}) {
  return apiFetch<Paged<{ statistics: LivestockPopulationStat[] }>>("/v1/statistics/livestock-population", { page_size: 50, ...opts });
}

export function getSeedDemandSummary(opts: { budget_year?: number; page?: number; page_size?: number } = {}) {
  return apiFetch<Paged<{ statistics: SeedDemandSummaryStat[] }>>("/v1/statistics/seed-demand/summary", { page_size: 50, ...opts });
}

export function getSeedDemandTrends(opts: { budget_year?: number; seed_class?: string; page?: number; page_size?: number } = {}) {
  return apiFetch<Paged<{ statistics: SeedDemandTrendStat[] }>>("/v1/statistics/seed-demand/trends", { page_size: 50, ...opts });
}

export function getSeedDemandByCrop(opts: { crop_code?: string; budget_year?: number; seed_class?: string; page?: number; page_size?: number } = {}) {
  return apiFetch<Paged<{ statistics: SeedDemandByCropStat[] }>>("/v1/statistics/seed-demand/by-crop", { page_size: 50, ...opts });
}

export function getHealthReady() {
  return apiFetch<HealthReady>("/health/ready");
}

export function getCropVariety(varietyCode: string, releaseVersion?: string) {
  return apiFetch<{ release: ReleaseData; variety: CropVarietyDetail }>(
    `/v1/crop-varieties/${encodeURIComponent(varietyCode)}`,
    { release_version: releaseVersion }
  );
}

export function getSeedVarieties(
  opts: {
    seed_crop_code?: string;
    crop_variety_code?: string;
    crop_type_code?: string;
    category_code?: string;
    match_status?: MatchStatus;
    release_year?: number;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}
) {
  return apiFetch<Paged<{ varieties: SeedVarietyData[] }>>("/v1/seed-varieties", { page_size: 25, ...opts });
}

export function getSeedVariety(seedVarietyCode: string, releaseVersion?: string) {
  return apiFetch<{ release: ReleaseData; variety: SeedVarietyData }>(
    `/v1/seed-varieties/${encodeURIComponent(seedVarietyCode)}`,
    { release_version: releaseVersion }
  );
}

export function getLivestockSpecies(opts: { search?: string; page?: number; page_size?: number } = {}) {
  return apiFetch<Paged<{ species: LivestockSpecies[] }>>("/v1/livestock/species", { page_size: 25, ...opts });
}

export function getLivestockBreeds(
  opts: {
    species_code?: string;
    breed_type?: LivestockBreedType;
    in_national_standard?: boolean;
    in_etlits_registry?: boolean;
    search?: string;
    page?: number;
    page_size?: number;
  } = {}
) {
  return apiFetch<Paged<{ breeds: LivestockBreed[] }>>("/v1/livestock/breeds", { page_size: 25, ...opts });
}

export function getLivestockReferenceData(releaseVersion?: string) {
  return apiFetch<{ release: ReleaseData } & LivestockReferenceDataBundle>("/v1/livestock/reference-data", {
    release_version: releaseVersion,
  });
}

export function getLivestockRegistryEntries(
  opts: { species_code?: string; status?: string; breed_id?: number; search?: string; page?: number; page_size?: number } = {}
) {
  return apiFetch<Paged<{ entries: LivestockRegistryEntry[] }>>("/v1/livestock/registry-entries", { page_size: 25, ...opts });
}

export function getLivestockRegistryValidation(
  opts: { species_code?: string; status?: string; has_issues?: boolean; page?: number; page_size?: number } = {}
) {
  return apiFetch<Paged<{ validations: LivestockRegistryValidation[] }>>("/v1/livestock/registry-validation", {
    page_size: 25,
    ...opts,
  });
}
