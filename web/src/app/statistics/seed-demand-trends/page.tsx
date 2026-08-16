import { getSeedDemandTrends } from "@/lib/api";
import { TableExport } from "@/components/table-export";

function fmt(v: string) {
  return Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

export default async function SeedDemandTrendsPage({
  searchParams,
}: {
  searchParams: Promise<{ seed_class?: string }>;
}) {
  const { seed_class } = await searchParams;
  const { statistics, total } = await getSeedDemandTrends({ seed_class, page_size: 200 });
  const classes = [...new Set(statistics.map((s) => s.seed_class))];
  const sorted = statistics
    .slice()
    .sort((a, b) => b.budget_year - a.budget_year || a.seed_class.localeCompare(b.seed_class));

  return (
    <div className="dt-card accent">
      <div className="dt-toolbar">
        <div className="seg">
          <a className={!seed_class ? "on" : undefined} href="/statistics/seed-demand-trends">
            All classes
          </a>
          {classes.map((c) => (
            <a key={c} className={seed_class === c ? "on" : undefined} href={`/statistics/seed-demand-trends?seed_class=${encodeURIComponent(c)}`}>
              {c}
            </a>
          ))}
        </div>
        <span className="dt-count">{total} rows</span>
        <TableExport
          headers={["Budget year", "Seed class", "Quantity demanded (qt)"]}
          rows={sorted.map((s) => [s.budget_year, s.seed_class, fmt(s.quantity_demanded)])}
          filename="seed_demand_trends"
        />
      </div>
      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr>
              <th style={{ width: 120 }}>Budget year</th>
              <th style={{ width: 160 }}>Seed class</th>
              <th className="num">Quantity demanded (qt)</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((s, i) => (
              <tr key={i}>
                <td className="mono strong">{s.budget_year}</td>
                <td>{s.seed_class}</td>
                <td className="num">{fmt(s.quantity_demanded)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
