import Link from "next/link";
import { getLivestockRegistryEntries } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { DtSearch } from "@/components/dt-search";
import { Pagination } from "@/components/pagination";
import { TableExport } from "@/components/table-export";

type Search = { q?: string; page?: string; species_code?: string; status?: string };

function qs(base: Record<string, string | number | undefined>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(base)) if (v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

function issueFlags(v: { breed_unrecognised: boolean; breed_outside_national_standard: boolean; breed_species_mismatch: boolean; production_type_species_mismatch: boolean }) {
  const flags: string[] = [];
  if (v.breed_unrecognised) flags.push("breed unrecognised");
  if (v.breed_outside_national_standard) flags.push("breed outside standard");
  if (v.breed_species_mismatch) flags.push("breed/species mismatch");
  if (v.production_type_species_mismatch) flags.push("production type mismatch");
  return flags;
}

export default async function LivestockRegistryEntriesPage({ searchParams }: { searchParams: Promise<Search> }) {
  const { q, page: pageStr, species_code, status } = await searchParams;
  const page = Number(pageStr ?? "1") || 1;

  const { entries, total, page_size } = await getLivestockRegistryEntries({ search: q, species_code, status, page, page_size: 25 });

  return (
    <div style={{ "--section-color": SECTION.livestock.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Livestock Registry Entry"
        subtitle={
          <>
            The release-scoped ET-LITS registry snapshot, with breed and production-type validation flags resolved
            against the current reference data. Fetched live from <code className="mono">GET /v1/livestock/registry-entries</code>.
          </>
        }
        color={SECTION.livestock.color}
        icon={SECTION.livestock.icon}
      />

      <div className="dt-card">
        <form className="dt-toolbar" method="get">
          <DtSearch name="q" defaultValue={q} placeholder="Search entries" />
          {species_code && (
            <Link className="chip" href={`/livestock/registry-entries${qs({ q, status })}`}>
              <span className="k">species</span><span className="v">{species_code}</span> ×
            </Link>
          )}
          {status && (
            <Link className="chip" href={`/livestock/registry-entries${qs({ q, species_code })}`}>
              <span className="k">status</span><span className="v">{status}</span> ×
            </Link>
          )}
          <span className="dt-count">{total} entries</span>
          <TableExport
            headers={["ID", "Species", "Breed", "Gender", "Location", "Condition", "Purpose", "Status", "Validation"]}
            rows={entries.map((e) => [
              e.id,
              e.species_code,
              e.breed_name,
              e.gender_code,
              e.location_type_code,
              e.body_condition_code,
              e.production_type_code,
              e.status,
              issueFlags(e.validation).join("; ") || "Clean",
            ])}
            filename="livestock_registry_entries"
          />
        </form>

        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 170 }}>ID</th>
                <th style={{ width: 110 }}>Species</th>
                <th style={{ width: 160 }}>Breed</th>
                <th style={{ width: 90 }}>Gender</th>
                <th style={{ width: 100 }}>Location</th>
                <th style={{ width: 90 }}>Condition</th>
                <th style={{ width: 110 }}>Purpose</th>
                <th style={{ width: 90 }}>Status</th>
                <th>Validation</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((e) => {
                const flags = issueFlags(e.validation);
                return (
                  <tr key={e.id}>
                    <td><span className="dt-code">{e.id}</span></td>
                    <td>
                      <Link className="chip" href={`/livestock/registry-entries${qs({ q, species_code: e.species_code, status })}`}>
                        <span className="v">{e.species_code}</span>
                      </Link>
                    </td>
                    <td className="dt-name">{e.breed_name}</td>
                    <td className="dt-dim">{e.gender_code}</td>
                    <td className="dt-dim">{e.location_type_code}</td>
                    <td className="dt-dim">{e.body_condition_code}</td>
                    <td className="dt-dim">{e.production_type_code}</td>
                    <td>
                      <Link className="chip" href={`/livestock/registry-entries${qs({ q, species_code, status: e.status })}`}>
                        <span className="v">{e.status}</span>
                      </Link>
                    </td>
                    <td>
                      {flags.length === 0 ? (
                        <span className="st-active">Clean</span>
                      ) : (
                        flags.map((f) => <span className="badge warn" key={f} style={{ marginRight: 4 }}>{f}</span>)
                      )}
                    </td>
                  </tr>
                );
              })}
              {entries.length === 0 && (
                <tr>
                  <td colSpan={9} className="dt-dim" style={{ textAlign: "center", padding: 24 }}>
                    No registry entries match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination total={total} page={page} pageSize={page_size} href={(p) => `/livestock/registry-entries${qs({ q, species_code, status, page: p })}`} />
      </div>
    </div>
  );
}
