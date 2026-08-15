import Link from "next/link";

export function Pagination({
  total,
  page,
  pageSize,
  href,
}: {
  total: number;
  page: number;
  pageSize: number;
  href: (page: number) => string;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="dt-foot">
      <span className="dt-range">
        {total === 0 ? 0 : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total}
      </span>
      <div className="dt-pages">
        <Link className={page <= 1 ? "off" : ""} href={href(page - 1)} aria-label="Previous page">
          ‹
        </Link>
        <span className="cur">{page}</span>
        <Link className={page >= totalPages ? "off" : ""} href={href(page + 1)} aria-label="Next page">
          ›
        </Link>
      </div>
    </div>
  );
}
