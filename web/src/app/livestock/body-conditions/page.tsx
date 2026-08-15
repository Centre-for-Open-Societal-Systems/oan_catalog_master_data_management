import { getLivestockReferenceData } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { TableExport } from "@/components/table-export";

export default async function LivestockBodyConditionsPage() {
  const { body_conditions } = await getLivestockReferenceData();

  return (
    <div style={{ "--section-color": SECTION.livestock.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Livestock Body Condition"
        subtitle={
          <>
            The 5-point body condition score (BCS) scale. Fetched live from{" "}
            <code className="mono">GET /v1/livestock/reference-data</code>.
          </>
        }
        color={SECTION.livestock.color}
        icon={SECTION.livestock.icon}
      />

      <div className="dt-card">
        <div className="dt-toolbar">
          <span className="dt-count">{body_conditions.length} conditions</span>
          <TableExport
            headers={["Score", "Condition", "Fatness", "ET-LITS label", "Description"]}
            rows={body_conditions.map((b) => [`BCS${b.bcs_score}`, b.condition_label, b.fatness_label, b.etlits_label ?? "", b.description ?? ""])}
            filename="livestock_body_conditions"
          />
        </div>
        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th className="num" style={{ width: 70 }}>Score</th>
                <th style={{ width: 130 }}>Condition</th>
                <th style={{ width: 130 }}>Fatness</th>
                <th style={{ width: 140 }}>ET-LITS label</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {body_conditions.map((b) => (
                <tr key={b.code}>
                  <td className="dt-num"><span className="dt-code">BCS{b.bcs_score}</span></td>
                  <td className="dt-name">{b.condition_label}</td>
                  <td>{b.fatness_label}</td>
                  <td className="dt-dim">{b.etlits_label ?? "—"}</td>
                  <td className="dt-dim">{b.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
