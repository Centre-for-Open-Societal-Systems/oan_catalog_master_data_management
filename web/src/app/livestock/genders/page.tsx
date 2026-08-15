import { getLivestockReferenceData } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { TableExport } from "@/components/table-export";

export default async function LivestockGendersPage() {
  const { genders } = await getLivestockReferenceData();

  return (
    <div style={{ "--section-color": SECTION.livestock.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Livestock Gender"
        subtitle={
          <>
            The full national-standard sex enumeration. Fetched live from{" "}
            <code className="mono">GET /v1/livestock/reference-data</code>.
          </>
        }
        color={SECTION.livestock.color}
        icon={SECTION.livestock.icon}
      />

      <div className="dt-card">
        <div className="dt-toolbar">
          <span className="dt-count">{genders.length} genders</span>
          <TableExport
            headers={["Code", "Name", "ET-LITS", "Description"]}
            rows={genders.map((g) => [g.code, g.display_name, g.in_etlits_registry ? "Yes" : "No", g.description ?? ""])}
            filename="livestock_genders"
          />
        </div>
        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 160 }}>Code</th>
                <th style={{ width: 160 }}>Name</th>
                <th style={{ width: 110 }}>ET-LITS</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {genders.map((g) => (
                <tr key={g.code}>
                  <td><span className="dt-code">{g.code}</span></td>
                  <td className="dt-name">{g.display_name}</td>
                  <td>{g.in_etlits_registry ? <span className="st-active">Yes</span> : <span className="dt-dim">No</span>}</td>
                  <td className="dt-dim">{g.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
