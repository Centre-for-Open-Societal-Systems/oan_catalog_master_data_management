import Link from "next/link";

export function CountPill({ count, label, href }: { count: number | null; label: string; href: string }) {
  if (!count) return <span className="dt-dim">0</span>;
  return (
    <Link className="count-pill" href={href}>
      <span className="n">{count}</span> {label}
      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m9 6 6 6-6 6" />
      </svg>
    </Link>
  );
}
