import Link from "next/link";
import { notFound } from "next/navigation";
import { getCatalogueValues, getCropVariety } from "@/lib/api";
import type { CropVarietySourceRecord } from "@/lib/types";
import { SECTION, sectionForCatalogue } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { ImagePreview } from "@/components/image-preview";
import { TableExport } from "@/components/table-export";

export default async function CatalogueValuePage({
  params,
}: {
  params: Promise<{ code: string; value: string }>;
}) {
  const { code, value } = await params;

  // crop_variety has its own dedicated detail endpoint with the full agronomic
  // record (yield/rainfall/altitude ranges, characteristics, source records) —
  // and at 1,359 rows it also exceeds the API's 1,000-row page_size cap, so the
  // generic "list the whole catalogue and find by code" approach below can't
  // reach every variety anyway.
  if (code === "crop_variety") {
    return <CropVarietyDetail varietyCode={decodeURIComponent(value)} />;
  }
  if (code === "crop") {
    return <CropDetail cropCode={decodeURIComponent(value)} />;
  }

  let data;
  try {
    // Every other catalogue here tops out at 129 rows, so one page_size:1000
    // call always returns the whole set — no generic "get one value" endpoint
    // exists. This assumption breaks if a non-variety catalogue ever exceeds
    // 1,000 rows; crop_variety already did, which is why it's special-cased.
    data = await getCatalogueValues(code, { page_size: 1000 });
  } catch {
    notFound();
  }
  const v = data.values.find((x) => x.code === decodeURIComponent(value));
  if (!v) notFound();

  const metaEntries = Object.entries(v.metadata ?? {});
  const section = sectionForCatalogue(code);

  return (
    <div style={{ "--section-color": section.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow={<><Link href="/catalogues">Catalogues</Link> · <Link href={`/catalogues/${code}`}>{code}</Link> · value</>}
        title={v.display_name}
        color={section.color}
        icon={section.icon}
      />

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 18, alignItems: "start" }}>
        <div>
          <div className="card accent">
            <div className="card-head">
              <h2 className="card-title">Identity</h2>
            </div>
            <div className="card-body">
              <dl className="kv">
                <div className="kv-row"><dt>Code</dt><dd className="mono">{v.code}</dd></div>
                <div className="kv-row"><dt>Catalogue</dt><dd><Link className="chip" href={`/catalogues/${code}`}><span className="k">catalogue</span><span className="v">{code}</span></Link></dd></div>
                <div className="kv-row"><dt>Parent code</dt><dd>{v.parent_code ? <span className="mono">{v.parent_code}</span> : <span className="dim">— none —</span>}</dd></div>
                <div className="kv-row"><dt>Status</dt><dd><span className={`badge ${v.status === "ACTIVE" ? "ok" : "mute"}`}>{v.status}</span></dd></div>
                <div className="kv-row"><dt>Sort order</dt><dd className="mono">{v.sort_order ?? "—"}</dd></div>
                <div className="kv-row"><dt>Valid from</dt><dd className="mono">{v.valid_from ?? "— open —"}</dd></div>
                <div className="kv-row"><dt>Valid to</dt><dd className="mono">{v.valid_to ?? "— open —"}</dd></div>
                {v.semantic_roles.length > 0 && (
                  <div className="kv-row">
                    <dt>Semantic roles</dt>
                    <dd>{v.semantic_roles.map((r) => <span className="chip" key={r}><span className="v">{r}</span></span>)}</dd>
                  </div>
                )}
              </dl>
            </div>
          </div>

          {metaEntries.length > 0 && (
            <div className="card">
              <div className="card-head">
                <h2 className="card-title">Metadata</h2>
                <span className="card-note">{metaEntries.length} keys · from the seeded release</span>
              </div>
              <div className="card-body">
                <dl className="kv">
                  {metaEntries.map(([k, val]) => (
                    <div className="kv-row" key={k}>
                      <dt className="mono">{k}</dt>
                      <dd>{String(val)}</dd>
                    </div>
                  ))}
                </dl>
              </div>
            </div>
          )}
        </div>

        <div className="card">
          <div className="card-head">
            <h2 className="card-title">Related values</h2>
          </div>
          <div className="card-body">
            {v.relations.length === 0 ? (
              <p className="dim">No relations on this value.</p>
            ) : (
              v.relations.map((r, i) => (
                <Link
                  key={i}
                  href={`/catalogues/${r.target_catalogue_code}/${encodeURIComponent(r.target_code)}`}
                  className="chip"
                  style={{ display: "flex", justifyContent: "space-between", padding: "8px 10px", marginBottom: 6 }}
                >
                  <span>
                    <span className="k" style={{ display: "block" }}>{r.type.replaceAll("_", " ")}</span>
                    <span className="v">{r.target_display_name}</span>
                  </span>
                  <span className="dim mono">{r.target_catalogue_code}·{r.target_code}</span>
                </Link>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

async function CropDetail({ cropCode }: { cropCode: string }) {
  let data;
  try {
    data = await getCatalogueValues("crop", { page_size: 1000 });
  } catch {
    notFound();
  }
  const v = data.values.find((x) => x.code === cropCode);
  if (!v) notFound();

  const section = SECTION.crop;
  const m = v.metadata ?? {};
  const str = (key: string) => (typeof m[key] === "string" ? (m[key] as string) : null);
  const num = (key: string) => (typeof m[key] === "number" ? (m[key] as number) : null);
  const category = v.relations.find((r) => r.type === "category");
  const ecoZone = v.relations.find((r) => r.type === "preferred_ecological_zone");
  const imageUrl = str("image_url");

  return (
    <div style={{ "--section-color": section.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow={<><Link href="/catalogues">Catalogues</Link> · <Link href="/catalogues/crop">crop</Link> · value</>}
        title={v.display_name}
        color={section.color}
        icon={section.icon}
      />

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 18, alignItems: "start" }}>
        <div>
          <div className="card accent">
            <div className="card-head">
              <h2 className="card-title">Identity</h2>
            </div>
            <div className="card-body">
              <dl className="kv">
                <div className="kv-row"><dt>Code</dt><dd className="mono">{v.code}</dd></div>
                <div className="kv-row"><dt>Name</dt><dd>{v.display_name}</dd></div>
                <div className="kv-row"><dt>Scientific name</dt><dd style={{ fontStyle: "italic" }}>{str("scientific_name") ?? "—"}</dd></div>
                <div className="kv-row"><dt>Status</dt><dd><span className={`badge ${v.status === "ACTIVE" ? "ok" : "mute"}`}>{v.status}</span></dd></div>
                <div className="kv-row">
                  <dt>Category</dt>
                  <dd>
                    {category ? (
                      <Link className="chip" href={`/catalogues/crop_category/${encodeURIComponent(category.target_code)}`}>
                        <span className="v">{category.target_display_name}</span>
                      </Link>
                    ) : "—"}
                  </dd>
                </div>
                <div className="kv-row"><dt>Varieties count</dt><dd className="mono">{num("varieties_count") ?? "—"}</dd></div>
              </dl>
            </div>
          </div>

          {str("description") && (
            <div className="card">
              <div className="card-head">
                <h2 className="card-title">Description</h2>
              </div>
              <div className="card-body">
                <p style={{ margin: 0, whiteSpace: "pre-line" }}>{str("description")}</p>
              </div>
            </div>
          )}

          <div className="card">
            <div className="card-head">
              <h2 className="card-title">Agronomy</h2>
            </div>
            <div className="card-body">
              <dl className="kv">
                <div className="kv-row"><dt>Known for</dt><dd>{str("known_for") ?? "—"}</dd></div>
                <div className="kv-row"><dt>Field inspections needed</dt><dd className="mono">{num("num_field_inspection_needed") ?? "—"}</dd></div>
                <div className="kv-row"><dt>Isolation distance</dt><dd className="mono">{num("isolation_distance") != null ? `${num("isolation_distance")} m` : "—"}</dd></div>
                <div className="kv-row">
                  <dt>Preferred ecological zone</dt>
                  <dd>
                    {ecoZone ? (
                      <Link className="chip" href={`/catalogues/ecological_zone/${encodeURIComponent(ecoZone.target_code)}`}>
                        <span className="v">{ecoZone.target_display_name}</span>
                      </Link>
                    ) : "—"}
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <h2 className="card-title">Image</h2>
          </div>
          <div className="card-body">
            {imageUrl ? <ImagePreview src={imageUrl} alt={v.display_name} /> : <p className="dim" style={{ margin: 0 }}>No image on record.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}

function range(min: string | number | null, max: string | number | null, unit: string) {
  if (min == null && max == null) return null;
  if (min != null && max != null && min !== max) return `${min}–${max} ${unit}`;
  return `${min ?? max} ${unit}`;
}

async function CropVarietyDetail({ varietyCode }: { varietyCode: string }) {
  let data;
  try {
    data = await getCropVariety(varietyCode);
  } catch {
    notFound();
  }
  const { variety } = data;
  const section = SECTION.crop;

  return (
    <div style={{ "--section-color": section.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow={<><Link href="/catalogues">Catalogues</Link> · <Link href="/catalogues/crop_variety">crop_variety</Link> · value</>}
        title={variety.display_name}
        color={section.color}
        icon={section.icon}
        meta={<div><span>Source records</span>{variety.source_records.length}</div>}
      />

      <div className="card accent">
        <div className="card-head">
          <h2 className="card-title">Identity</h2>
        </div>
        <div className="card-body">
          <dl className="kv">
            <div className="kv-row"><dt>Code</dt><dd className="mono">{variety.code}</dd></div>
            <div className="kv-row"><dt>Status</dt><dd><span className={`badge ${variety.status === "ACTIVE" ? "ok" : "mute"}`}>{variety.status}</span></dd></div>
            <div className="kv-row">
              <dt>Crop type</dt>
              <dd><Link className="chip" href={`/catalogues/crop_type/${encodeURIComponent(variety.crop_type.code)}`}><span className="k">crop_type</span><span className="v">{variety.crop_type.display_name}</span></Link></dd>
            </div>
            <div className="kv-row">
              <dt>Category</dt>
              <dd><Link className="chip" href={`/catalogues/crop_taxonomy_category/${encodeURIComponent(variety.category.code)}`}><span className="k">category</span><span className="v">{variety.category.display_name}</span></Link></dd>
            </div>
          </dl>
        </div>
      </div>

      {variety.source_records.map((rec) => (
        <SourceRecordCard key={rec.source_record_code} rec={rec} />
      ))}
    </div>
  );
}

function SourceRecordCard({ rec }: { rec: CropVarietySourceRecord }) {
  const altitude = range(rec.altitude_min_m, rec.altitude_max_m, "m");
  const rainfall = range(rec.rainfall_min_mm, rec.rainfall_max_mm, "mm");
  const maturity = range(rec.days_to_maturity_min, rec.days_to_maturity_max, "days");
  const yieldResearch = range(rec.yield_research_min_qt_ha, rec.yield_research_max_qt_ha, "qt/ha");
  const yieldFarmer = range(rec.yield_farmer_min_qt_ha, rec.yield_farmer_max_qt_ha, "qt/ha");

  return (
    <div className="card">
      <div className="card-head">
        <h2 className="card-title">{rec.centre}</h2>
        <span className="card-note">
          {rec.source_record_code} · released {rec.release_year ?? rec.release_year_raw}
        </span>
      </div>
      <div className="card-body">
        <dl className="kv">
          {altitude && <div className="kv-row"><dt>Altitude</dt><dd>{altitude}</dd></div>}
          {rainfall && <div className="kv-row"><dt>Rainfall</dt><dd>{rainfall}</dd></div>}
          {maturity && <div className="kv-row"><dt>Days to maturity</dt><dd>{maturity}</dd></div>}
          {yieldResearch && <div className="kv-row"><dt>Yield (research)</dt><dd>{yieldResearch}</dd></div>}
          {yieldFarmer && <div className="kv-row"><dt>Yield (farmer)</dt><dd>{yieldFarmer}</dd></div>}
          {rec.seed_rate_kg_ha && <div className="kv-row"><dt>Seed rate</dt><dd>{rec.seed_rate_kg_ha} kg/ha</dd></div>}
          {rec.planting_date_text && <div className="kv-row"><dt>Planting date</dt><dd>{rec.planting_date_text}</dd></div>}
          {rec.adaptation_area && <div className="kv-row"><dt>Adaptation area</dt><dd>{rec.adaptation_area}</dd></div>}
          {rec.crop_pest_reaction && <div className="kv-row"><dt>Pest reaction</dt><dd>{rec.crop_pest_reaction}</dd></div>}
          {rec.source_url && (
            <div className="kv-row">
              <dt>Source</dt>
              <dd><a href={rec.source_url} target="_blank" rel="noreferrer">{rec.source_url}</a></dd>
            </div>
          )}
        </dl>

        {rec.characteristics.length > 0 && (
          <div className="table-wrap" style={{ marginTop: 12 }}>
            <div className="dt-toolbar" style={{ padding: "0 0 8px" }}>
              <TableExport
                headers={["Characteristic", "Value"]}
                rows={rec.characteristics.map((c) => [c.display_name, `${c.raw_value}${c.unit_code ? ` ${c.unit_code}` : ""}`])}
                filename={`crop_variety_characteristics_${rec.source_record_code}`}
              />
            </div>
            <table className="grid">
              <thead>
                <tr>
                  <th style={{ width: 220 }}>Characteristic</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {rec.characteristics.map((c) => (
                  <tr key={c.code}>
                    <td className="strong">{c.display_name}</td>
                    <td>
                      {c.raw_value}
                      {c.unit_code ? ` ${c.unit_code}` : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
