import Link from "next/link";
import { getSeedVarieties } from "@/lib/api";
import type { MatchStatus } from "@/lib/types";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { RecordActions } from "@/components/record-actions";
import { DtSearch } from "@/components/dt-search";
import { Pagination } from "@/components/pagination";
import { TableExport } from "@/components/table-export";

type Search = { q?: string; match_status?: MatchStatus; page?: string; seed_crop_code?: string; seed_crop_name?: string };

function qs(base: Record<string, string | number | undefined>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(base)) if (v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

const STATUS_BADGE: Record<MatchStatus, string> = {
  MATCHED: "ok",
  UNRESOLVED: "warn",
  CONFLICT: "bad",
};

export default async function SeedVarietiesPage({ searchParams }: { searchParams: Promise<Search> }) {
  const { q, match_status, page: pageStr, seed_crop_code, seed_crop_name } = await searchParams;
  const page = Number(pageStr ?? "1") || 1;

  const { varieties, total, page_size } = await getSeedVarieties({ search: q, match_status, seed_crop_code, page, page_size: 25 });

  return (
    <div style={{ "--section-color": SECTION.seed.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Seed Variety"
        subtitle={
          <>
            Ethiopia Seed System registry entries, reconciled against the crop variety taxonomy where possible.
            Fetched live from <code className="mono">GET /v1/seed-varieties</code>.
          </>
        }
        color={SECTION.seed.color}
        icon={SECTION.seed.icon}
      />

      <div className="dt-card">
        <form className="dt-toolbar" method="get">
          <DtSearch name="q" defaultValue={q} placeholder="Search variety or crop name" />
          <div className="seg">
            <Link className={!match_status ? "on" : undefined} href={`/seed-varieties${qs({ q, seed_crop_code, seed_crop_name })}`}>All</Link>
            <Link className={match_status === "MATCHED" ? "on" : undefined} href={`/seed-varieties${qs({ q, match_status: "MATCHED", seed_crop_code, seed_crop_name })}`}>Matched</Link>
            <Link className={match_status === "UNRESOLVED" ? "on" : undefined} href={`/seed-varieties${qs({ q, match_status: "UNRESOLVED", seed_crop_code, seed_crop_name })}`}>Unresolved</Link>
            <Link className={match_status === "CONFLICT" ? "on" : undefined} href={`/seed-varieties${qs({ q, match_status: "CONFLICT", seed_crop_code, seed_crop_name })}`}>Conflict</Link>
          </div>
          {seed_crop_code && (
            <Link className="chip" href={`/seed-varieties${qs({ q, match_status })}`}>
              <span className="k">seed crop</span>
              <span className="v">{seed_crop_name ?? seed_crop_code}</span> ×
            </Link>
          )}
          <span className="dt-count">{total} varieties</span>
          <TableExport
            headers={["Variety", "Seed crop", "Match", "Matched crop variety", "Release", "Maintainer"]}
            rows={varieties.map((v) => [
              v.display_name,
              v.seed_crop.display_name,
              v.match_status,
              v.matched_crop_variety?.display_name ?? "",
              v.release_year ?? "",
              v.maintainer ?? "",
            ])}
            filename="seed_varieties"
          />
          <RecordActions basePath="/seed-varieties" newLabel="New variety" />
        </form>

        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 280 }}>Variety</th>
                <th style={{ width: 180 }}>Seed crop</th>
                <th style={{ width: 130 }}>Match</th>
                <th style={{ width: 200 }}>Matched crop variety</th>
                <th style={{ width: 90 }}>Release</th>
                <th>Maintainer</th>
              </tr>
            </thead>
            <tbody>
              {varieties.map((v) => (
                <tr key={v.code}>
                  <td className="dt-name">
                    <Link className="row-link" href={`/seed-varieties/${encodeURIComponent(v.code)}`}>
                      {v.display_name}
                    </Link>
                  </td>
                  <td>{v.seed_crop.display_name}</td>
                  <td>
                    <span className={`badge ${STATUS_BADGE[v.match_status]}`}>{v.match_status}</span>
                  </td>
                  <td>
                    {v.matched_crop_variety ? (
                      <Link className="chip" href={`/catalogues/crop_variety/${encodeURIComponent(v.matched_crop_variety.code)}`}>
                        <span className="v">{v.matched_crop_variety.display_name}</span>
                      </Link>
                    ) : (
                      <span className="dt-dim">—</span>
                    )}
                  </td>
                  <td className="mono dt-dim">{v.release_year ?? "—"}</td>
                  <td className="dt-dim">{v.maintainer ?? "—"}</td>
                </tr>
              ))}
              {varieties.length === 0 && (
                <tr>
                  <td colSpan={6} className="dt-dim" style={{ textAlign: "center", padding: 24 }}>
                    No varieties match this search.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination total={total} page={page} pageSize={page_size} href={(p) => `/seed-varieties${qs({ q, match_status, seed_crop_code, seed_crop_name, page: p })}`} />
      </div>
    </div>
  );
}
