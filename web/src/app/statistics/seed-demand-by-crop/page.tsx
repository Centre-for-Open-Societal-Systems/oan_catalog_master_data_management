import Link from "next/link";
import { getSeedDemandByCrop } from "@/lib/api";
import { DtSearch } from "@/components/dt-search";
import { TableExport } from "@/components/table-export";

type Search = { q?: string; budget_year?: string; seed_class?: string };

function fmt(v: string) {
  return Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

export default async function SeedDemandByCropPage({ searchParams }: { searchParams: Promise<Search> }) {
  const { q, budget_year, seed_class } = await searchParams;
  const { statistics, total } = await getSeedDemandByCrop({ budget_year: budget_year ? Number(budget_year) : undefined, seed_class, page_size: 500 });
  const filtered = q ? statistics.filter((s) => s.crop_name.toLowerCase().includes(q.toLowerCase())) : statistics;
  const sorted = filtered.slice().sort((a, b) => Number(b.quantity_demanded) - Number(a.quantity_demanded));

  return (
    <div className="dt-card accent">
      <form className="dt-toolbar" method="get">
        <DtSearch name="q" defaultValue={q} placeholder="Search crop" />
        <input type="hidden" name="budget_year" value={budget_year ?? ""} />
        <input type="hidden" name="seed_class" value={seed_class ?? ""} />
        <span className="dt-count">{sorted.length} of {total} rows</span>
        <TableExport
          headers={["Crop", "Budget year", "Seed class", "Quantity demanded (qt)"]}
          rows={sorted.map((s) => [s.crop_name, s.budget_year, s.seed_class, fmt(s.quantity_demanded)])}
          filename="seed_demand_by_crop"
        />
      </form>
      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr>
              <th style={{ width: 260 }}>Crop</th>
              <th style={{ width: 120 }}>Budget year</th>
              <th style={{ width: 160 }}>Seed class</th>
              <th className="num">Quantity demanded (qt)</th>
            </tr>
          </thead>
          <tbody>
            {sorted.slice(0, 200).map((s, i) => (
              <tr key={i}>
                <td className="strong">
                  <Link className="row-link" href={`/catalogues/crop/${encodeURIComponent(s.crop_code)}`}>
                    {s.crop_name}
                  </Link>
                </td>
                <td className="mono">{s.budget_year}</td>
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
