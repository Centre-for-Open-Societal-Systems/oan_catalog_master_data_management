import { getLivestockReferenceData } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { TableExport } from "@/components/table-export";

export default async function LivestockRecordStatusesPage() {
  const { record_statuses } = await getLivestockReferenceData();
  const sorted = record_statuses.slice().sort((a, b) => a.sort_order - b.sort_order);

  return (
    <div style={{ "--section-color": SECTION.livestock.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Livestock Record Status"
        subtitle={
          <>
            The registry-entry workflow states, in review order. Fetched live from{" "}
            <code className="mono">GET /v1/livestock/reference-data</code>.
          </>
        }
        color={SECTION.livestock.color}
        icon={SECTION.livestock.icon}
      />

      <div className="dt-card">
        <div className="dt-toolbar">
          <span className="dt-count">{record_statuses.length} statuses</span>
          <TableExport
            headers={["Order", "Status", "Live master data", "Description"]}
            rows={sorted.map((r) => [r.sort_order, r.display_name, r.is_live_master_data ? "Yes" : "No", r.description ?? ""])}
            filename="livestock_record_statuses"
          />
        </div>
        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th className="num" style={{ width: 70 }}>Order</th>
                <th style={{ width: 160 }}>Status</th>
                <th style={{ width: 140 }}>Live master data</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => (
                <tr key={r.code}>
                  <td className="dt-num dt-dim">{r.sort_order}</td>
                  <td>
                    {r.is_live_master_data ? <span className="st-active">{r.display_name}</span> : <span className="st-retired">{r.display_name}</span>}
                  </td>
                  <td>{r.is_live_master_data ? "Yes" : <span className="dt-dim">No</span>}</td>
                  <td className="dt-dim">{r.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
