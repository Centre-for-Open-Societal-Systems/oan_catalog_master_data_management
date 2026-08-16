import { getLivestockReferenceData } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { TableExport } from "@/components/table-export";

export default async function LivestockProductionTypesPage() {
  const { production_types } = await getLivestockReferenceData();

  return (
    <div style={{ "--section-color": SECTION.livestock.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Livestock Production Type"
        subtitle={
          <>
            Why an animal is kept, and which species each purpose is valid for. Fetched live from{" "}
            <code className="mono">GET /v1/livestock/reference-data</code>.
          </>
        }
        color={SECTION.livestock.color}
        icon={SECTION.livestock.icon}
      />

      <div className="dt-card">
        <div className="dt-toolbar">
          <span className="dt-count">{production_types.length} production types</span>
          <TableExport
            headers={["Code", "National standard", "ET-LITS", "Valid species", "Description"]}
            rows={production_types.map((p) => [
              p.display_name,
              p.in_national_standard ? "Yes" : "No",
              p.in_etlits_registry ? "Yes" : "No",
              p.valid_species.map((s) => s.display_name).join("; "),
              p.description ?? "",
            ])}
            filename="livestock_production_types"
          />
        </div>
        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 170 }}>Code</th>
                <th style={{ width: 130 }}>National standard</th>
                <th style={{ width: 110 }}>ET-LITS</th>
                <th style={{ width: 260 }}>Valid species</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {production_types.map((p) => (
                <tr key={p.code}>
                  <td><span className="dt-code">{p.display_name}</span></td>
                  <td>{p.in_national_standard ? <span className="st-active">Yes</span> : <span className="dt-dim">No</span>}</td>
                  <td>{p.in_etlits_registry ? <span className="st-active">Yes</span> : <span className="dt-dim">No</span>}</td>
                  <td>
                    {p.valid_species.length === 0 ? (
                      <span className="dt-dim">none</span>
                    ) : (
                      p.valid_species.map((s) => (
                        <span className="chip" key={s.code}><span className="v">{s.display_name}</span></span>
                      ))
                    )}
                  </td>
                  <td className="dt-dim">{p.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
