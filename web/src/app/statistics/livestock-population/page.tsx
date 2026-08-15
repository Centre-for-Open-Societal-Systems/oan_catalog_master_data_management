import { getLivestockPopulation } from "@/lib/api";
import { TableExport } from "@/components/table-export";

const SPECIES_COLOR: Record<string, string> = {
  camel: "var(--s1)",
  cattle: "var(--s2)",
  goat: "var(--s3)",
  sheep: "var(--s4)",
};

function fmt(n: number) {
  return n.toLocaleString("en-US");
}

export default async function LivestockPopulationPage() {
  const { statistics, total } = await getLivestockPopulation({ page_size: 200 });

  const years = [...new Set(statistics.map((s) => s.census_year))].sort((a, b) => a - b);
  const species = [...new Set(statistics.map((s) => s.species_code))].sort(
    (a, b) => Object.keys(SPECIES_COLOR).indexOf(a) - Object.keys(SPECIES_COLOR).indexOf(b)
  );
  const maxPop = Math.max(...statistics.map((s) => s.population_total), 1);

  const chartW = 1000, chartH = 240, padL = 56, padB = 24, padT = 10;
  const plotW = chartW - padL - 10, plotH = chartH - padB - padT;
  const groupW = plotW / years.length;
  const barW = Math.min(22, (groupW - 8) / species.length);

  const byYearSpecies = new Map(statistics.map((s) => [`${s.census_year}:${s.species_code}`, s]));
  const sortedStats = statistics
    .slice()
    .sort((a, b) => a.species_code.localeCompare(b.species_code) || a.census_year - b.census_year);

  return (
    <div className="dt-card accent">
      <div className="dt-toolbar">
        <span className="dt-count">{total} rows · {species.length} species · {years.length} census years</span>
        <TableExport
          headers={["Species", "Census year", "Population total", "Source records"]}
          rows={sortedStats.map((s) => [
            s.species_code[0].toUpperCase() + s.species_code.slice(1),
            s.census_year,
            s.population_total,
            s.source_record_count,
          ])}
          filename="livestock_population"
        />
      </div>
      <div className="card-body">
        <svg viewBox={`0 0 ${chartW} ${chartH}`} role="img" aria-label="Livestock population by species and census year">
          {[0, 0.25, 0.5, 0.75, 1].map((f) => {
            const y = padT + plotH * (1 - f);
            return (
              <g key={f}>
                <line x1={padL} y1={y} x2={chartW - 10} y2={y} stroke="var(--line)" strokeWidth={1} />
                <text x={padL - 8} y={y + 3} textAnchor="end" fontSize={10} fill="var(--ink-3)">
                  {(maxPop * f / 1_000_000).toFixed(0)}M
                </text>
              </g>
            );
          })}
          {years.map((year, yi) => {
            const groupX = padL + yi * groupW;
            return (
              <g key={year}>
                {species.map((sp, si) => {
                  const rec = byYearSpecies.get(`${year}:${sp}`);
                  const v = rec?.population_total ?? 0;
                  const h = (v / maxPop) * plotH;
                  const x = groupX + si * barW + (groupW - species.length * barW) / 2;
                  return (
                    <rect
                      key={sp}
                      x={x}
                      y={padT + plotH - h}
                      width={barW - 2}
                      height={h}
                      rx={2}
                      fill={SPECIES_COLOR[sp]}
                    >
                      <title>{`${sp} · ${year} · ${fmt(v)} head`}</title>
                    </rect>
                  );
                })}
                <text x={groupX + groupW / 2} y={chartH - 6} textAnchor="middle" fontSize={10} fill="var(--ink-3)">
                  {year}
                </text>
              </g>
            );
          })}
          <line x1={padL} y1={padT + plotH} x2={chartW - 10} y2={padT + plotH} stroke="var(--line-strong)" />
        </svg>
        <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
          {species.map((sp) => (
            <span key={sp} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
              <i style={{ width: 10, height: 10, borderRadius: 2, background: SPECIES_COLOR[sp], display: "inline-block" }} />
              {sp[0].toUpperCase() + sp.slice(1)}
            </span>
          ))}
        </div>
      </div>

      <div className="table-wrap">
        <table className="grid">
          <thead>
            <tr>
              <th style={{ width: 140 }}>Species</th>
              <th style={{ width: 120 }}>Census year</th>
              <th className="num" style={{ width: 160 }}>Population total</th>
              <th className="num">Source records</th>
            </tr>
          </thead>
          <tbody>
            {sortedStats.map((s, i) => (
                <tr key={i}>
                  <td className="strong">{s.species_code[0].toUpperCase() + s.species_code.slice(1)}</td>
                  <td className="mono">{s.census_year}</td>
                  <td className="num">{fmt(s.population_total)}</td>
                  <td className="num dim">{fmt(s.source_record_count)}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
