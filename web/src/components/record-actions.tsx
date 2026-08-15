import Link from "next/link";

export function RecordActions({ basePath, newLabel = "New" }: { basePath: string; newLabel?: string }) {
  return (
    <>
      <Link className="btn btn-outline" href={`${basePath}/upload`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 16V4M12 4 7 9M12 4l5 5" />
          <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
        </svg>
        Upload CSV
      </Link>
      <Link className="btn btn-primary" href={`${basePath}/new`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 5v14M5 12h14" />
        </svg>
        {newLabel}
      </Link>
    </>
  );
}
