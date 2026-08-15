import Link from "next/link";

export default function NotFound() {
  return (
    <div className="hint" style={{ margin: 24 }}>
      <span>
        Not found. <Link href="/catalogues">Back to catalogues</Link>
      </span>
    </div>
  );
}
