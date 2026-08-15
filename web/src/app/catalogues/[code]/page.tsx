import Link from "next/link";
import { notFound } from "next/navigation";
import { getCatalogueValues, getSeedVarieties } from "@/lib/api";
import { CATEGORY_SWATCH, sectionForCatalogue } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { RecordActions } from "@/components/record-actions";
import { DtSearch } from "@/components/dt-search";
import { Pagination } from "@/components/pagination";
import { CountPill } from "@/components/count-pill";
import { TableExport } from "@/components/table-export";

type Params = { code: string };
type Search = {
  q?: string;
  status?: string;
  page?: string;
  relation_type?: string;
  related_catalogue_code?: string;
  related_value_code?: string;
  related_value_name?: string;
};

function qs(base: Record<string, string | number | undefined>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(base)) if (v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export default async function CatalogueValuesPage({
  params,
  searchParams,
}: {
  params: Promise<Params>;
  searchParams: Promise<Search>;
}) {
  const { code } = await params;

  if (code === "crop_taxonomy_category") {
    return <CropCategoryTable searchParams={searchParams} />;
  }
  if (code === "ecological_zone") {
    return <EcologicalZoneTable searchParams={searchParams} />;
  }
  if (code === "crop") {
    return <CropTable searchParams={searchParams} />;
  }
  return <GenericCatalogueTable code={code} searchParams={searchParams} />;
}

/* ---- Crop — code, name, scientific name, category, status, varieties count ---- */

async function CropTable({ searchParams }: { searchParams: Promise<Search> }) {
  const { q, status, page: pageStr } = await searchParams;
  const page = Number(pageStr ?? "1") || 1;
  const section = sectionForCatalogue("crop");

  let data;
  try {
    data = await getCatalogueValues("crop", { search: q, status, page, page_size: 25 });
  } catch {
    notFound();
  }
  const { values, total, page_size } = data;

  // The crop catalogue's own `varieties_count` metadata is computed from
  // legacy source rows, not from the crop_variety taxonomy — it doesn't match
  // the number of crop_variety rows crop_type reconciliation actually turns
  // up (e.g. Maize: metadata says 99, the live crop_type relation says 84).
  // Rather than show a pill whose number disagrees with where it lands, fetch
  // the live crop_type-relation count for rows that have a reconciled
  // taxonomy_type_code, same as the Crop Type page's own Varieties column.
  const varietyCounts = await Promise.all(
    values.map((v) => {
      const typeCode = typeof v.metadata?.taxonomy_type_code === "string" ? v.metadata.taxonomy_type_code : null;
      if (!typeCode) return Promise.resolve(null);
      return getCatalogueValues("crop_variety", {
        relation_type: "crop_type",
        related_catalogue_code: "crop_type",
        related_value_code: typeCode,
        page_size: 1,
      })
        .then((r) => ({ count: r.total, typeCode }))
        .catch(() => null);
    })
  );

  return (
    <div style={{ "--section-color": section.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow={<><Link href="/catalogues">Catalogues</Link> · crop</>}
        title="Crop"
        subtitle={
          <>
            {total} crops. Fetched live from <code className="mono">GET /v1/catalogues/crop/values</code>.
          </>
        }
        color={section.color}
        icon={section.icon}
      />

      <div className="dt-card">
        <form className="dt-toolbar" method="get">
          <DtSearch name="q" defaultValue={q} placeholder="Search by name or code" />
          <div className="seg">
            <Link className={!status ? "on" : undefined} href={`/catalogues/crop${qs({ q })}`}>All</Link>
            <Link className={status === "ACTIVE" ? "on" : undefined} href={`/catalogues/crop${qs({ q, status: "ACTIVE" })}`}>Active</Link>
            <Link className={status === "RETIRED" ? "on" : undefined} href={`/catalogues/crop${qs({ q, status: "RETIRED" })}`}>Retired</Link>
          </div>
          <span className="dt-count">{total} crops</span>
          <TableExport
            headers={["Code", "Name", "Scientific name", "Category", "Status", "Varieties"]}
            rows={values.map((v, i) => [
              v.code,
              v.display_name,
              typeof v.metadata?.scientific_name === "string" ? v.metadata.scientific_name : "",
              v.relations.find((r) => r.type === "category")?.target_display_name ?? "",
              v.status,
              varietyCounts[i]?.count ?? 0,
            ])}
            filename="crop"
          />
        </form>

        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 70 }}>Code</th>
                <th style={{ width: 220 }}>Name</th>
                <th style={{ width: 170 }}>Scientific name</th>
                <th style={{ width: 160 }}>Category</th>
                <th style={{ width: 100 }}>Status</th>
                <th className="num" style={{ width: 100 }}>Varieties</th>
              </tr>
            </thead>
            <tbody>
              {values.map((v, i) => {
                const category = v.relations.find((r) => r.type === "category");
                const varietyInfo = varietyCounts[i];
                const varietyHref = varietyInfo
                  ? `/catalogues/crop_variety${qs({
                      relation_type: "crop_type",
                      related_catalogue_code: "crop_type",
                      related_value_code: varietyInfo.typeCode,
                      related_value_name: v.display_name,
                    })}`
                  : "";
                return (
                  <tr key={v.code}>
                    <td>
                      <Link className="dt-code" href={`/catalogues/crop/${encodeURIComponent(v.code)}`}>
                        {v.code}
                      </Link>
                    </td>
                    <td className="dt-name">
                      <Link className="row-link" href={`/catalogues/crop/${encodeURIComponent(v.code)}`}>
                        {v.display_name}
                      </Link>
                    </td>
                    <td className="dt-dim" style={{ fontStyle: "italic" }}>{typeof v.metadata?.scientific_name === "string" ? v.metadata.scientific_name : "—"}</td>
                    <td>
                      {category ? (
                        <Link className="chip" href={`/catalogues/crop_category/${encodeURIComponent(category.target_code)}`}>
                          <span className="v">{category.target_display_name}</span>
                        </Link>
                      ) : (
                        <span className="dt-dim">—</span>
                      )}
                    </td>
                    <td>
                      {v.status === "ACTIVE" ? <span className="st-active">Active</span> : <span className="st-retired">{v.status}</span>}
                    </td>
                    <td className="dt-num">
                      <CountPill count={varietyInfo?.count ?? null} label="varieties" href={varietyHref} />
                    </td>
                  </tr>
                );
              })}
              {values.length === 0 && (
                <tr>
                  <td colSpan={6} className="dt-dim" style={{ textAlign: "center", padding: 24 }}>
                    No crops match this search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination total={total} page={page} pageSize={page_size} href={(p) => `/catalogues/crop${qs({ q, status, page: p })}`} />
      </div>
    </div>
  );
}

/* ---- Ecological Zone — id, name, description only ----------------------- */

async function EcologicalZoneTable({ searchParams }: { searchParams: Promise<Search> }) {
  const { q } = await searchParams;
  const section = sectionForCatalogue("ecological_zone");

  let data;
  try {
    data = await getCatalogueValues("ecological_zone", { search: q, page_size: 100 });
  } catch {
    notFound();
  }
  const { values, total } = data;

  return (
    <div style={{ "--section-color": section.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow={<><Link href="/catalogues">Catalogues</Link> · ecological_zone</>}
        title="Ecological Zone"
        subtitle={
          <>
            {total} zones. Fetched live from <code className="mono">GET /v1/catalogues/ecological_zone/values</code>.
          </>
        }
        color={section.color}
        icon={section.icon}
      />

      <div className="dt-card">
        <form className="dt-toolbar" method="get">
          <DtSearch name="q" defaultValue={q} placeholder="Search by name or id" />
          <span className="dt-count">{total} zones</span>
          <TableExport
            headers={["ID", "Name", "Description"]}
            rows={values.map((v) => [v.code, v.display_name, typeof v.metadata?.description === "string" ? v.metadata.description : ""])}
            filename="ecological_zone"
          />
        </form>

        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 90 }}>ID</th>
                <th style={{ width: 200 }}>Name</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {values.map((v) => (
                <tr key={v.code}>
                  <td>
                    <Link className="dt-code" href={`/catalogues/ecological_zone/${encodeURIComponent(v.code)}`}>
                      {v.code}
                    </Link>
                  </td>
                  <td className="dt-name">
                    <Link className="row-link" href={`/catalogues/ecological_zone/${encodeURIComponent(v.code)}`}>
                      {v.display_name}
                    </Link>
                  </td>
                  <td className="dt-dim">{typeof v.metadata?.description === "string" ? v.metadata.description : "—"}</td>
                </tr>
              ))}
              {values.length === 0 && (
                <tr>
                  <td colSpan={3} className="dt-dim" style={{ textAlign: "center", padding: 24 }}>
                    No zones match this search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* ---- Crop Category — code, name, crop count only ----------------------- */

async function CropCategoryTable({ searchParams }: { searchParams: Promise<Search> }) {
  const { q, page: pageStr } = await searchParams;
  const page = Number(pageStr ?? "1") || 1;
  const section = sectionForCatalogue("crop_taxonomy_category");

  let data;
  try {
    data = await getCatalogueValues("crop_taxonomy_category", { search: q, page, page_size: 25 });
  } catch {
    notFound();
  }
  const { values, total, page_size } = data;

  const cropCounts = await Promise.all(
    values.map((v) =>
      getCatalogueValues("crop_type", {
        relation_type: "category",
        related_catalogue_code: "crop_taxonomy_category",
        related_value_code: v.code,
        page_size: 1,
      })
        .then((r) => r.total)
        .catch(() => null)
    )
  );

  return (
    <div style={{ "--section-color": section.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow={<><Link href="/catalogues">Catalogues</Link> · crop_taxonomy_category</>}
        title="Crop Category"
        subtitle={
          <>
            {total} categories. Fetched live from <code className="mono">GET /v1/catalogues/crop_taxonomy_category/values</code>.
          </>
        }
        color={section.color}
        icon={section.icon}
      />

      <div className="dt-card">
        <form className="dt-toolbar" method="get">
          <DtSearch name="q" defaultValue={q} placeholder="Search by name or code" />
          <span className="dt-count">{total} categories</span>
          <TableExport
            headers={["Code", "Name", "Crop count"]}
            rows={values.map((v, i) => [v.code, v.display_name, cropCounts[i] ?? 0])}
            filename="crop_taxonomy_category"
          />
          <RecordActions basePath="/catalogues/crop_taxonomy_category" />
        </form>

        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 260 }}>Code</th>
                <th>Name</th>
                <th className="num" style={{ width: 120 }}>Crop count</th>
              </tr>
            </thead>
            <tbody>
              {values.map((v, i) => {
                const swatch = CATEGORY_SWATCH[v.code];
                const count = cropCounts[i];
                const cropTypeHref = `/catalogues/crop_type${qs({
                  relation_type: "category",
                  related_catalogue_code: "crop_taxonomy_category",
                  related_value_code: v.code,
                  related_value_name: v.display_name,
                })}`;
                return (
                  <tr key={v.code} data-cat={swatch?.key}>
                    <td>
                      <Link className="dt-code" href={`/catalogues/crop_taxonomy_category/${encodeURIComponent(v.code)}`}>
                        {v.code}
                      </Link>
                    </td>
                    <td className="dt-name">
                      <Link className="row-link" href={`/catalogues/crop_taxonomy_category/${encodeURIComponent(v.code)}`}>
                        {v.display_name}
                      </Link>
                    </td>
                    <td className="dt-num">
                      <CountPill count={count} label="crop types" href={cropTypeHref} />
                    </td>
                  </tr>
                );
              })}
              {values.length === 0 && (
                <tr>
                  <td colSpan={3} className="dt-dim" style={{ textAlign: "center", padding: 24 }}>
                    No categories match this search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination total={total} page={page} pageSize={page_size} href={(p) => `/catalogues/crop_taxonomy_category${qs({ q, page: p })}`} />
      </div>
    </div>
  );
}

/* ---- Every other catalogue --------------------------------------------- */

async function GenericCatalogueTable({ code, searchParams }: { code: string; searchParams: Promise<Search> }) {
  const { q, status, page: pageStr, relation_type, related_catalogue_code, related_value_code, related_value_name } = await searchParams;
  const page = Number(pageStr ?? "1") || 1;

  let data;
  try {
    data = await getCatalogueValues(code, {
      search: q,
      status,
      page,
      page_size: 25,
      relation_type,
      related_catalogue_code,
      related_value_code,
    });
  } catch {
    notFound();
  }
  const { catalogue, values, total, page_size } = data;
  const section = sectionForCatalogue(code);
  const isCropType = code === "crop_type";
  const isSeedCrop = code === "seed_crop";
  const relationActive = Boolean(related_value_code);

  // Crop Type and Seed Crop each get a "Varieties" column — how many
  // crop_variety / seed-variety rows link back to this one — fetched per
  // row for just the current page, same pattern as the catalogues overview
  // page's per-catalogue counts.
  let varietyCounts: (number | null)[] | null = null;
  if (isCropType) {
    varietyCounts = await Promise.all(
      values.map((v) =>
        getCatalogueValues("crop_variety", {
          relation_type: "crop_type",
          related_catalogue_code: "crop_type",
          related_value_code: v.code,
          page_size: 1,
        })
          .then((r) => r.total)
          .catch(() => null)
      )
    );
  } else if (isSeedCrop) {
    varietyCounts = await Promise.all(
      values.map((v) =>
        getSeedVarieties({ seed_crop_code: v.code, page_size: 1 })
          .then((r) => r.total)
          .catch(() => null)
      )
    );
  }

  return (
    <div style={{ "--section-color": section.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow={<><Link href="/catalogues">Catalogues</Link> · {catalogue.code}</>}
        title={catalogue.display_name}
        subtitle={
          <>
            {total} values, {catalogue.is_hierarchical ? "hierarchical" : "flat"}. Fetched live from{" "}
            <code className="mono">GET /v1/catalogues/{code}/values</code>.
          </>
        }
        color={section.color}
        icon={section.icon}
      />

      <div className="dt-card">
        <form className="dt-toolbar" method="get">
          <DtSearch name="q" defaultValue={q} placeholder="Search by display name or code" />
          <div className="seg">
            <Link className={!status ? "on" : undefined} href={`/catalogues/${code}${qs({ q })}`}>All</Link>
            <Link className={status === "ACTIVE" ? "on" : undefined} href={`/catalogues/${code}${qs({ q, status: "ACTIVE" })}`}>Active</Link>
            <Link className={status === "RETIRED" ? "on" : undefined} href={`/catalogues/${code}${qs({ q, status: "RETIRED" })}`}>Retired</Link>
          </div>
          {relationActive && (
            <Link className="chip" href={`/catalogues/${code}${qs({ q, status })}`}>
              <span className="k">{related_catalogue_code}</span>
              <span className="v">{related_value_name ?? related_value_code}</span> ×
            </Link>
          )}
          <span className="dt-count">{total} values</span>
          <TableExport
            headers={["Code", "Display name", "Status", "Sort", isSeedCrop || isCropType ? "Varieties" : "Relations"]}
            rows={values.map((v, i) => [
              v.code,
              v.display_name,
              v.status,
              v.sort_order ?? "",
              isSeedCrop || isCropType
                ? varietyCounts?.[i] ?? 0
                : v.relations.map((r) => `${r.type}: ${r.target_display_name}`).join("; "),
            ])}
            filename={code}
          />
          <RecordActions basePath={`/catalogues/${code}`} />
        </form>

        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 90 }}>Code</th>
                <th style={{ width: 260 }}>Display name</th>
                <th style={{ width: 100 }}>Status</th>
                <th className="num" style={{ width: 90 }}>Sort</th>
                {isSeedCrop ? <th className="num" style={{ width: 110 }}>Varieties</th> : <th>Relations</th>}
                {isCropType && <th className="num" style={{ width: 110 }}>Varieties</th>}
              </tr>
            </thead>
            <tbody>
              {values.map((v, i) => {
                const varietyCount = varietyCounts?.[i] ?? null;
                const varietyHref = isCropType
                  ? `/catalogues/crop_variety${qs({
                      relation_type: "crop_type",
                      related_catalogue_code: "crop_type",
                      related_value_code: v.code,
                      related_value_name: v.display_name,
                    })}`
                  : `/seed-varieties${qs({ seed_crop_code: v.code, seed_crop_name: v.display_name })}`;
                return (
                  <tr key={v.code}>
                    <td>
                      <Link className="dt-code" href={`/catalogues/${code}/${encodeURIComponent(v.code)}`}>
                        {v.code}
                      </Link>
                    </td>
                    <td className="dt-name">
                      <Link className="row-link" href={`/catalogues/${code}/${encodeURIComponent(v.code)}`}>
                        {v.display_name}
                      </Link>
                    </td>
                    <td>
                      {v.status === "ACTIVE" ? <span className="st-active">Active</span> : <span className="st-retired">{v.status}</span>}
                    </td>
                    <td className="dt-num dt-dim">{v.sort_order ?? "—"}</td>
                    {isSeedCrop ? (
                      <td className="dt-num">
                        <CountPill count={varietyCount} label="varieties" href={varietyHref} />
                      </td>
                    ) : (
                      <td>
                        {v.relations.length === 0 ? (
                          <span className="dt-dim">—</span>
                        ) : (
                          v.relations.map((r, ri) => (
                            <span className="chip" key={ri}>
                              <span className="k">{r.type.replaceAll("_", " ")}</span>
                              <span className="v">{r.target_display_name}</span>
                            </span>
                          ))
                        )}
                      </td>
                    )}
                    {isCropType && (
                      <td className="dt-num">
                        <CountPill count={varietyCount} label="varieties" href={varietyHref} />
                      </td>
                    )}
                  </tr>
                );
              })}
              {values.length === 0 && (
                <tr>
                  <td colSpan={6} className="dt-dim" style={{ textAlign: "center", padding: 24 }}>
                    No values match this search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination
          total={total}
          page={page}
          pageSize={page_size}
          href={(p) => `/catalogues/${code}${qs({ q, status, page: p, relation_type, related_catalogue_code, related_value_code, related_value_name })}`}
        />
      </div>
    </div>
  );
}
