import Link from "next/link";
import { notFound } from "next/navigation";
import { getSeedVariety } from "@/lib/api";
import type { MatchStatus } from "@/lib/types";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";

const STATUS_BADGE: Record<MatchStatus, string> = {
  MATCHED: "ok",
  UNRESOLVED: "warn",
  CONFLICT: "bad",
};

const STATUS_COLOR: Record<MatchStatus, string> = {
  MATCHED: "var(--accent)",
  UNRESOLVED: "var(--amber)",
  CONFLICT: "var(--brick)",
};

export default async function SeedVarietyPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;

  let data;
  try {
    data = await getSeedVariety(decodeURIComponent(code));
  } catch {
    notFound();
  }
  const v = data.variety;

  return (
    <div style={{ "--section-color": SECTION.seed.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow={<><Link href="/seed-varieties">Seed Variety</Link> · value</>}
        title={v.display_name}
        color={SECTION.seed.color}
        icon={SECTION.seed.icon}
        meta={<div style={{ color: STATUS_COLOR[v.match_status] }}><span>Match</span>{v.match_status}</div>}
      />

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 18, alignItems: "start" }}>
        <div>
          <div className="card accent">
            <div className="card-head">
              <h2 className="card-title">Identity</h2>
            </div>
            <div className="card-body">
              <dl className="kv">
                <div className="kv-row"><dt>Code</dt><dd className="mono">{v.code}</dd></div>
                <div className="kv-row"><dt>Status</dt><dd><span className={`badge ${v.status === "ACTIVE" ? "ok" : "mute"}`}>{v.status}</span></dd></div>
                <div className="kv-row"><dt>Crop (raw)</dt><dd>{v.crop_name_raw}</dd></div>
                <div className="kv-row"><dt>Common name (raw)</dt><dd>{v.common_name_raw}</dd></div>
                {v.category_raw && <div className="kv-row"><dt>Category (raw)</dt><dd>{v.category_raw}</dd></div>}
                <div className="kv-row"><dt>Release</dt><dd>{v.release_raw ?? v.release_year ?? "—"}</dd></div>
                <div className="kv-row"><dt>Maintainer</dt><dd>{v.maintainer ?? "—"}</dd></div>
                <div className="kv-row"><dt>Classification</dt><dd>{v.source_classification ?? "—"}</dd></div>
                <div className="kv-row">
                  <dt>Source</dt>
                  <dd><a href={v.details_url} target="_blank" rel="noreferrer">ethioseed.moa.gov.et ↗</a></dd>
                </div>
              </dl>
            </div>
          </div>

          <div className="card">
            <div className="card-head">
              <h2 className="card-title">Reconciliation</h2>
              <span className="card-note">against the crop variety taxonomy</span>
            </div>
            <div className="card-body">
              <dl className="kv">
                <div className="kv-row">
                  <dt>Match status</dt>
                  <dd><span className={`badge ${STATUS_BADGE[v.match_status]}`}>{v.match_status}</span></dd>
                </div>
                <div className="kv-row"><dt>Match method</dt><dd className="mono">{v.match_method}</dd></div>
                {v.review_note && (
                  <div className="kv-row">
                    <dt>Review note</dt>
                    <dd>{v.review_note.split(";").map((n) => <span className="chip" key={n}><span className="v">{n}</span></span>)}</dd>
                  </div>
                )}
              </dl>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <h2 className="card-title">Related values</h2>
          </div>
          <div className="card-body">
            <Link href={`/catalogues/seed_crop/${encodeURIComponent(v.seed_crop.code)}`} className="chip" style={{ display: "flex", justifyContent: "space-between", padding: "8px 10px", marginBottom: 6 }}>
              <span><span className="k" style={{ display: "block" }}>seed crop</span><span className="v">{v.seed_crop.display_name}</span></span>
            </Link>
            {v.matched_crop_variety ? (
              <>
                <Link href={`/catalogues/crop_variety/${encodeURIComponent(v.matched_crop_variety.code)}`} className="chip" style={{ display: "flex", justifyContent: "space-between", padding: "8px 10px", marginBottom: 6 }}>
                  <span><span className="k" style={{ display: "block" }}>crop variety</span><span className="v">{v.matched_crop_variety.display_name}</span></span>
                </Link>
                {v.crop_type && (
                  <Link href={`/catalogues/crop_type/${encodeURIComponent(v.crop_type.code)}`} className="chip" style={{ display: "flex", justifyContent: "space-between", padding: "8px 10px", marginBottom: 6 }}>
                    <span><span className="k" style={{ display: "block" }}>crop type</span><span className="v">{v.crop_type.display_name}</span></span>
                  </Link>
                )}
                {v.category && (
                  <Link href={`/catalogues/crop_taxonomy_category/${encodeURIComponent(v.category.code)}`} className="chip" style={{ display: "flex", justifyContent: "space-between", padding: "8px 10px", marginBottom: 6 }}>
                    <span><span className="k" style={{ display: "block" }}>category</span><span className="v">{v.category.display_name}</span></span>
                  </Link>
                )}
              </>
            ) : (
              <p className="dim">
                No crop variety match yet — this entry hasn&apos;t been reconciled against the variety taxonomy.
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
