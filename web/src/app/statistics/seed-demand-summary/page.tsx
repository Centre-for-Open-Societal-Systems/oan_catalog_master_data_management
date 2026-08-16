import { getSeedDemandSummary } from "@/lib/api";
import { TableExport } from "@/components/table-export";

function fmt(v: string) {
  return Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

export default async function SeedDemandSummaryPage() {
  const { statistics, total } = await getSeedDemandSummary({ page_size: 200 });
  const sorted = statistics.slice().sort((a, b) => a.budget_year - b.budget_year);

  return (
    <div className="dt-card accent">
      <div className="dt-toolbar">
        <span className="dt-count">{total} budget years</span>
        <TableExport
          headers={["Budget year", "Total entries", "Quantity demanded (qt)", "Avg per entry (qt)", "Estimated land (ha)"]}
          rows={sorted.map((s) => [
            s.budget_year,
            s.total_entries,
            fmt(s.total_quantity_demanded),
            fmt(s.average_quantity_per_entry),
            fmt(s.total_estimated_land_ha),
          ])}
          filename="seed_demand_summary"
        />
      </div>
      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr>
              <th style={{ width: 120 }}>Budget year</th>
              <th className="num" style={{ width: 140 }}>Total entries</th>
              <th className="num" style={{ width: 180 }}>Quantity demanded (qt)</th>
              <th className="num" style={{ width: 170 }}>Avg per entry (qt)</th>
              <th className="num">Estimated land (ha)</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((s) => (
              <tr key={s.budget_year}>
                <td className="mono strong">{s.budget_year}</td>
                <td className="num">{s.total_entries.toLocaleString("en-US")}</td>
                <td className="num">{fmt(s.total_quantity_demanded)}</td>
                <td className="num dim">{fmt(s.average_quantity_per_entry)}</td>
                <td className="num dim">{fmt(s.total_estimated_land_ha)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
