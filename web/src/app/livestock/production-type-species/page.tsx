import Link from "next/link";
import { getLivestockReferenceData } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { TableExport } from "@/components/table-export";

export default async function LivestockProductionTypeSpeciesPage() {
  const { production_types } = await getLivestockReferenceData();

  const rows = production_types.flatMap((p) =>
    p.valid_species.map((s) => ({
      production_type: p.display_name,
      production_type_code: p.code,
      species: s.display_name,
      species_code: s.code,
    }))
  );

  return (
    <div style={{ "--section-color": SECTION.livestock.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Livestock Production Type Species"
        subtitle={
          <>
            The production-type-to-species validity matrix, flattened to one row per pair — derived from each
            production type&apos;s <code className="mono">valid_species</code> list, the same data shown on the
            Production Type tab.
          </>
        }
        color={SECTION.livestock.color}
        icon={SECTION.livestock.icon}
      />

      <div className="dt-card">
        <div className="dt-toolbar">
          <span className="dt-count">{rows.length} pairs</span>
          <TableExport
            headers={["Production type", "Species"]}
            rows={rows.map((r) => [r.production_type, r.species])}
            filename="livestock_production_type_species"
          />
        </div>
        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 260 }}>Production type</th>
                <th>Species</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td>
                    <Link className="chip" href={`/livestock/production-types`}>
                      <span className="v">{r.production_type}</span>
                    </Link>
                  </td>
                  <td>
                    <Link className="chip" href={`/livestock/breeds?species_code=${encodeURIComponent(r.species_code)}&species_name=${encodeURIComponent(r.species)}`}>
                      <span className="v">{r.species}</span>
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
