"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { ICONS } from "@/lib/icons";

const DASHBOARD_PATH = "/dashboard";
const FALLBACK = "/catalogues";

/**
 * Opens the dashboard, carrying the current location so it can be returned to,
 * and turns into that return trip once the dashboard is open.
 */
export function DashboardLink() {
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const onDashboard = pathname === DASHBOARD_PATH;

  const from = search && !onDashboard ? `${pathname}?${search}` : pathname;
  const back = new URLSearchParams(search).get("from");
  const href = onDashboard
    ? back && back.startsWith("/") && !back.startsWith("//")
      ? back
      : FALLBACK
    : `${DASHBOARD_PATH}?from=${encodeURIComponent(from)}`;

  return (
    <Link
      className="chrome-btn chrome-btn-wide"
      href={href}
      aria-current={onDashboard ? "page" : undefined}
      title={onDashboard ? "Back to the catalogue console" : "Catalogue dashboard"}
    >
      <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        {onDashboard ? ICONS.back : ICONS.dashboard}
      </svg>
      {onDashboard ? "Back" : "Dashboard"}
    </Link>
  );
}
