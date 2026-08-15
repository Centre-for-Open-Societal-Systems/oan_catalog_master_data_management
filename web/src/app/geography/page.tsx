import Link from "next/link";
import { getGeographyLevels, getGeographyUnits } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { RecordActions } from "@/components/record-actions";
import { DtSearch } from "@/components/dt-search";
import { Pagination } from "@/components/pagination";
import { TableExport } from "@/components/table-export";

type Search = { level?: string; parent?: string; q?: string; page?: string };

function qs(base: Record<string, string | number | undefined>) {
  const p = new URLSearchParams();
  for (const [k, v] of Object.entries(base)) if (v !== undefined && v !== "") p.set(k, String(v));
  const s = p.toString();
  return s ? `?${s}` : "";
}

export default async function GeographyPage({ searchParams }: { searchParams: Promise<Search> }) {
  const { level: levelParam, parent, q, page: pageStr } = await searchParams;
  const page = Number(pageStr ?? "1") || 1;

  const { levels } = await getGeographyLevels();
  const level = levelParam ?? levels[0]?.code ?? "";
  const currentLevel = levels.find((l) => l.code === level);

  const { units, total, page_size } = await getGeographyUnits({
    level_code: level || undefined,
    parent_code: parent,
    search: q,
    page,
    page_size: 25,
  });

  return (
    <div style={{ "--section-color": SECTION.geography.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Geography"
        subtitle={
          <>
            Admin hierarchy for the active release. Fetched live from <code className="mono">GET /v1/geography/units</code>.
          </>
        }
        color={SECTION.geography.color}
        icon={SECTION.geography.icon}
      />

      <div className="dt-card">
        <form className="dt-toolbar" method="get">
          <DtSearch name="q" defaultValue={q} placeholder="Search name, code or alias" />
          {currentLevel && (
            <span className="chip">
              <span className="k">level</span><span className="v">{currentLevel.display_name}</span>
            </span>
          )}
          {parent && (
            <Link className="chip" href={`/geography${qs({ level, q })}`}>
              <span className="k">under</span><span className="v">{parent}</span> ×
            </Link>
          )}
          <span className="dt-count">{total} units</span>
          <TableExport
            headers={["Code", "Display name", "Amharic", "Parent", "Coordinates", "Status", "Aliases"]}
            rows={units.map((u) => [
              u.code,
              u.display_name,
              u.display_name_amh ?? "",
              u.parent_code ?? "",
              u.latitude && u.longitude ? `${u.latitude}, ${u.longitude}` : "",
              u.metadata?.data_quality === "MISSING_PARENT" ? "MISSING_PARENT" : u.status,
              u.aliases.join("; "),
            ])}
            filename={`geography_${level || "units"}`}
          />
          <RecordActions basePath="/geography" />
        </form>

        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 110 }}>Code</th>
                <th style={{ width: 180 }}>Display name</th>
                <th style={{ width: 140 }}>Amharic</th>
                <th style={{ width: 110 }}>Parent</th>
                <th className="num" style={{ width: 170 }}>Coordinates</th>
                <th style={{ width: 90 }}>Status</th>
                <th>Aliases</th>
              </tr>
            </thead>
            <tbody>
              {units.map((u) => {
                const flagged = u.metadata?.data_quality === "MISSING_PARENT";
                return (
                  <tr key={u.code}>
                    <td><span className="dt-code">{u.code}</span></td>
                    <td className="dt-name">{u.display_name}</td>
                    <td className="dt-dim">{u.display_name_amh ?? "—"}</td>
                    <td>
                      {u.parent_code ? (
                        <Link className="chip" href={`/geography${qs({ level, parent: u.parent_code })}`}>
                          {u.parent_code}
                        </Link>
                      ) : (
                        <span className="dt-dim">— root —</span>
                      )}
                    </td>
                    <td className="dt-num dt-dim">{u.latitude && u.longitude ? `${u.latitude}, ${u.longitude}` : "—"}</td>
                    <td>
                      {flagged ? (
                        <span className="badge warn">MISSING_PARENT</span>
                      ) : u.status === "ACTIVE" ? (
                        <span className="st-active">Active</span>
                      ) : (
                        <span className="st-retired">{u.status}</span>
                      )}
                    </td>
                    <td>{u.aliases.length ? u.aliases.map((a) => <span className="chip" key={a}><span className="v">{a}</span></span>) : <span className="dt-dim">—</span>}</td>
                  </tr>
                );
              })}
              {units.length === 0 && (
                <tr>
                  <td colSpan={7} className="dt-dim" style={{ textAlign: "center", padding: 24 }}>
                    No units match this filter.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <Pagination total={total} page={page} pageSize={page_size} href={(p) => `/geography${qs({ level, parent, q, page: p })}`} />
      </div>
    </div>
  );
}
