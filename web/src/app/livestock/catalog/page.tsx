import Link from "next/link";
import { getLivestockSpecies } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { DtSearch } from "@/components/dt-search";
import { Pagination } from "@/components/pagination";
import { TableExport } from "@/components/table-export";

type Search = { q?: string; page?: string };

function qs(base: Record<string, string | number | undefined>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(base)) if (v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export default async function LivestockCatalogPage({ searchParams }: { searchParams: Promise<Search> }) {
  const { q, page: pageStr } = await searchParams;
  const page = Number(pageStr ?? "1") || 1;

  const { species, total, page_size } = await getLivestockSpecies({ search: q, page, page_size: 25 });

  return (
    <div style={{ "--section-color": SECTION.livestock.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Livestock Catalog"
        subtitle={
          <>
            Species tracked across the LIS population dashboard and the ET-LITS registry. Fetched live from{" "}
            <code className="mono">GET /v1/livestock/species</code>.
          </>
        }
        color={SECTION.livestock.color}
        icon={SECTION.livestock.icon}
      />

      <div className="dt-card">
        <form className="dt-toolbar" method="get">
          <DtSearch name="q" defaultValue={q} placeholder="Search species" />
          <span className="dt-count">{total} species</span>
          <TableExport
            headers={["Code", "Name", "Scientific name", "Description", "LIS", "ET-LITS"]}
            rows={species.map((s) => [
              s.code,
              s.display_name,
              s.scientific_name ?? "",
              s.description ?? "",
              s.in_lis_population ? "Yes" : "",
              s.in_etlits_registry ? "Yes" : "",
            ])}
            filename="livestock_catalog"
          />
        </form>

        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 130 }}>Code</th>
                <th style={{ width: 160 }}>Name</th>
                <th style={{ width: 160 }}>Scientific name</th>
                <th>Description</th>
                <th style={{ width: 90 }}>LIS</th>
                <th style={{ width: 90 }}>ET-LITS</th>
              </tr>
            </thead>
            <tbody>
              {species.map((s) => (
                <tr key={s.code} style={s.chart_color ? ({ "--cat": s.chart_color } as React.CSSProperties) : undefined}>
                  <td><span className="dt-code">{s.code}</span></td>
                  <td className="dt-name">
                    <Link className="row-link" href={`/livestock/breeds?species_code=${encodeURIComponent(s.code)}&species_name=${encodeURIComponent(s.display_name)}`}>
                      {s.display_name}
                    </Link>
                  </td>
                  <td className="dt-dim" style={{ fontStyle: "italic" }}>{s.scientific_name ?? "—"}</td>
                  <td className="dt-dim">{s.description ?? "—"}</td>
                  <td>{s.in_lis_population ? <span className="st-active">Yes</span> : <span className="dt-dim">—</span>}</td>
                  <td>{s.in_etlits_registry ? <span className="st-active">Yes</span> : <span className="dt-dim">—</span>}</td>
                </tr>
              ))}
              {species.length === 0 && (
                <tr>
                  <td colSpan={6} className="dt-dim" style={{ textAlign: "center", padding: 24 }}>
                    No species match this search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination total={total} page={page} pageSize={page_size} href={(p) => `/livestock/catalog${qs({ q, page: p })}`} />
      </div>
    </div>
  );
}
