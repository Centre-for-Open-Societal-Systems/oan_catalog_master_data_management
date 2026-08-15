import Link from "next/link";
import { getCatalogueValues, getCatalogues } from "@/lib/api";
import { SECTION, sectionForCatalogue } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { TableExport } from "@/components/table-export";

export default async function CataloguesPage() {
  const { catalogues } = await getCatalogues();

  const counts = await Promise.all(
    catalogues.map((c) => getCatalogueValues(c.code, { page_size: 1 }).then((r) => r.total).catch(() => null))
  );

  const exportHeaders = ["Code", "Display name", "Domain", "Structure", "Values"];
  const exportRows = catalogues.map((c, i) => [
    c.code,
    c.display_name,
    c.domain ?? "",
    c.is_hierarchical ? "Hierarchical" : "Flat",
    counts[i] ?? "",
  ]);

  return (
    <div style={{ "--section-color": SECTION.catalogues.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Catalogues"
        subtitle={
          <>
            Code lists published in the active release. Fetched live from <code className="mono">GET /v1/catalogues</code>.
          </>
        }
        color={SECTION.catalogues.color}
        icon={SECTION.catalogues.icon}
      />

      <div className="dt-card">
        <div className="dt-toolbar">
          <span className="dt-count">{catalogues.length} catalogues</span>
          <TableExport headers={exportHeaders} rows={exportRows} filename="catalogues" />
        </div>
        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 150 }}>Code</th>
                <th style={{ width: 200 }}>Display name</th>
                <th style={{ width: 130 }}>Domain</th>
                <th style={{ width: 130 }}>Structure</th>
                <th className="num" style={{ width: 100 }}>Values</th>
              </tr>
            </thead>
            <tbody>
              {catalogues.map((c, i) => {
                const section = sectionForCatalogue(c.code);
                return (
                  <tr key={c.code} style={{ "--cat": section.color } as React.CSSProperties}>
                    <td>
                      <Link className="dt-code" href={`/catalogues/${c.code}`}>
                        {c.code}
                      </Link>
                    </td>
                    <td className="dt-name">
                      <Link className="row-link" href={`/catalogues/${c.code}`}>
                        {c.display_name}
                      </Link>
                    </td>
                    <td>{c.domain ? <span className="chip"><span className="v">{c.domain}</span></span> : <span className="dt-dim">—</span>}</td>
                    <td><span className="badge mute">{c.is_hierarchical ? "Hierarchical" : "Flat"}</span></td>
                    <td className="dt-num">{counts[i] ?? "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
