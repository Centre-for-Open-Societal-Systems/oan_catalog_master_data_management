import Link from "next/link";
import type { ReactNode } from "react";
import { SectionHeader } from "./section-header";

export function ComingSoon({
  eyebrow,
  title,
  color,
  icon,
  backHref,
  backLabel,
  kind,
  bullets,
}: {
  eyebrow: ReactNode;
  title: string;
  color: string;
  icon: ReactNode;
  backHref: string;
  backLabel: string;
  kind: "form" | "upload";
  bullets: string[];
}) {
  return (
    <div style={{ "--section-color": color } as React.CSSProperties}>
      <SectionHeader eyebrow={eyebrow} title={title} color={color} icon={icon} />

      <div className="card accent">
        <div className="card-head">
          <h2 className="card-title">Not wired up yet</h2>
          <span className="badge warn">Planned</span>
        </div>
        <div className="card-body">
          <p style={{ marginTop: 0 }}>
            {kind === "form"
              ? "This app is read-only end to end — catalogue-api has no write endpoints, so there's nowhere for a new record to be saved yet."
              : "This app is read-only end to end — catalogue-api has no import endpoint, so an uploaded file has nowhere to go yet."}
          </p>
          <p className="dim" style={{ fontSize: 12.5 }}>Once a write path exists, this screen is expected to include:</p>
          <ul style={{ margin: "6px 0 0", paddingLeft: 20, color: "var(--ink-2)", fontSize: 13 }}>
            {bullets.map((b) => (
              <li key={b} style={{ marginBottom: 4 }}>{b}</li>
            ))}
          </ul>
          <div style={{ marginTop: 16 }}>
            <Link className="btn btn-outline" href={backHref}>
              ← {backLabel}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
