export const ICONS = {
  catalogues: (
    <>
      <path d="M4 5h6v14H4zM14 5h6v14h-6z" />
      <path d="M4 9h6M14 9h6" />
    </>
  ),
  crop: (
    <>
      <path d="M12 21V13" />
      <path d="M12 13c0-4-3-7-7-7 0 4 3 7 7 7z" />
      <path d="M12 13c0-3 2.5-6 6-6 0 3-2.5 6-6 6z" />
    </>
  ),
  livestock: (
    <>
      <path d="M7 10c-2-1-3-3-2-5 2 0 4 1 5 3" />
      <path d="M17 10c2-1 3-3 2-5-2 0-4 1-5 3" />
      <path d="M6 13a6 6 0 0 1 12 0c0 4-3 7-6 7s-6-3-6-7z" />
    </>
  ),
  geography: (
    <>
      <path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z" />
      <path d="M9 4v14M15 6v14" />
    </>
  ),
  seed: <path d="M12 3c3 3 5 6.5 5 9.5a5 5 0 0 1-10 0C7 9.5 9 6 12 3z" />,
  statistics: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />,
  health: <path d="M2 12h4l2-6 4 12 2.5-7 1.5 3h6" />,
};

export const SECTION = {
  crop: { color: "var(--s1)", icon: ICONS.crop },
  livestock: { color: "var(--s2)", icon: ICONS.livestock },
  geography: { color: "var(--s4)", icon: ICONS.geography },
  seed: { color: "var(--s3)", icon: ICONS.seed },
  statistics: { color: "var(--s6)", icon: ICONS.statistics },
  catalogues: { color: "var(--accent)", icon: ICONS.catalogues },
  health: { color: "var(--accent)", icon: ICONS.health },
} as const;

const CATALOGUE_SECTION: Record<string, keyof typeof SECTION> = {
  crop: "crop",
  crop_category: "crop",
  ecological_zone: "crop",
  crop_type: "crop",
  crop_taxonomy_category: "crop",
  crop_variety: "crop",
  livestock_type: "livestock",
  seed_crop: "seed",
};

export function sectionForCatalogue(code: string) {
  return SECTION[CATALOGUE_SECTION[code] ?? "catalogues"];
}

/* Crop taxonomy category color tokens — see the tr[data-cat] rules in
   globals.css for what these mean and why there are only 8 of them, each
   individually valid but not mutually distinguishable at once. Keyed by the
   real catalogue_value codes from GET /v1/catalogues/crop_taxonomy_category/values. */
export const CATEGORY_SWATCH: Record<string, { key: string; label: string; hex: string }> = {
  "cereal":                                { key: "cereal",     label: "Cereal",     hex: "#E0BE00" },
  "food-legume":                           { key: "legume",     label: "Green 1",    hex: "#91AC34" },
  "fruit-and-vegetables":                  { key: "vegetable",  label: "Green 2",    hex: "#009147" },
  "industrial-crops":                      { key: "industrial", label: "Aqua Cyan",  hex: "#6FCCDD" },
  "oil-seeds":                             { key: "oil",        label: "Amber",      hex: "#C98A00" },
  "roots-and-tubers":                      { key: "root",       label: "Soil",       hex: "#625641" },
  "spices-condiments-medicinal-aromatic":  { key: "spice",      label: "Orange",     hex: "#FAA819" },
  "stimulant-crops":                       { key: "stimulant",  label: "Red",        hex: "#DB2727" },
};
