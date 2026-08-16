import Link from "next/link";
import { getLivestockBreeds } from "@/lib/api";
import type { LivestockBreedType } from "@/lib/types";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { DtSearch } from "@/components/dt-search";
import { Pagination } from "@/components/pagination";
import { TableExport } from "@/components/table-export";

type Search = {
  q?: string;
  page?: string;
  species_code?: string;
  species_name?: string;
  breed_type?: LivestockBreedType;
};

function qs(base: Record<string, string | number | undefined>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(base)) if (v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

const BREED_TYPES: LivestockBreedType[] = ["Indigenous", "Exotic", "Cross"];

export default async function LivestockBreedsPage({ searchParams }: { searchParams: Promise<Search> }) {
  const { q, page: pageStr, species_code, species_name, breed_type } = await searchParams;
  const page = Number(pageStr ?? "1") || 1;

  const { breeds, total, page_size } = await getLivestockBreeds({ search: q, species_code, breed_type, page, page_size: 25 });

  return (
    <div style={{ "--section-color": SECTION.livestock.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Livestock Breed"
        subtitle={
          <>
            National Livestock Data Standard breeds, cross-checked against the ET-LITS registry. Fetched live from{" "}
            <code className="mono">GET /v1/livestock/breeds</code>.
          </>
        }
        color={SECTION.livestock.color}
        icon={SECTION.livestock.icon}
      />

      <div className="dt-card">
        <form className="dt-toolbar" method="get">
          <DtSearch name="q" defaultValue={q} placeholder="Search breed" />
          <div className="seg">
            <Link className={!breed_type ? "on" : undefined} href={`/livestock/breeds${qs({ q, species_code, species_name })}`}>All</Link>
            {BREED_TYPES.map((t) => (
              <Link key={t} className={breed_type === t ? "on" : undefined} href={`/livestock/breeds${qs({ q, species_code, species_name, breed_type: t })}`}>
                {t}
              </Link>
            ))}
          </div>
          {species_code && (
            <Link className="chip" href={`/livestock/breeds${qs({ q, breed_type })}`}>
              <span className="k">species</span>
              <span className="v">{species_name ?? species_code}</span> ×
            </Link>
          )}
          <span className="dt-count">{total} breeds</span>
          <TableExport
            headers={["Breed code", "Name", "Species", "Type", "National standard", "ET-LITS", "Source"]}
            rows={breeds.map((b) => [
              b.breed_code ?? b.code,
              b.display_name,
              b.species.display_name,
              b.breed_type,
              b.in_national_standard ? "Yes" : "No",
              b.in_etlits_registry ? "Yes" : "No",
              b.source,
            ])}
            filename="livestock_breeds"
          />
        </form>

        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 100 }}>Breed code</th>
                <th style={{ width: 200 }}>Name</th>
                <th style={{ width: 140 }}>Species</th>
                <th style={{ width: 120 }}>Type</th>
                <th style={{ width: 130 }}>National standard</th>
                <th style={{ width: 110 }}>ET-LITS</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {breeds.map((b) => (
                <tr key={b.code}>
                  <td><span className="dt-code">{b.breed_code ?? b.code}</span></td>
                  <td className="dt-name">{b.display_name}{b.abbreviation ? <span className="dt-dim"> ({b.abbreviation})</span> : null}</td>
                  <td>
                    <Link className="chip" href={`/livestock/breeds${qs({ species_code: b.species.code, species_name: b.species.display_name })}`}>
                      <span className="v">{b.species.display_name}</span>
                    </Link>
                  </td>
                  <td><span className="badge mute">{b.breed_type}</span></td>
                  <td>{b.in_national_standard ? <span className="st-active">Yes</span> : <span className="dt-dim">No</span>}</td>
                  <td>{b.in_etlits_registry ? <span className="st-active">Yes</span> : <span className="dt-dim">No</span>}</td>
                  <td className="dt-dim">{b.source}</td>
                </tr>
              ))}
              {breeds.length === 0 && (
                <tr>
                  <td colSpan={7} className="dt-dim" style={{ textAlign: "center", padding: 24 }}>
                    No breeds match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination total={total} page={page} pageSize={page_size} href={(p) => `/livestock/breeds${qs({ q, species_code, species_name, breed_type, page: p })}`} />
      </div>
    </div>
  );
}
