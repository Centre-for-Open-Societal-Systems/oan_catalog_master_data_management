"use client";

import { usePathname } from "next/navigation";

const FULL_BLEED = ["/dashboard"];

/**
 * The console frame. The dashboard was designed to fill the width and divide
 * the viewport height between its bands, so on that route the sidebar drops
 * away and the main area loses its padding.
 */
export function AppShell({ sidebar, children }: { sidebar: React.ReactNode; children: React.ReactNode }) {
  const fullBleed = FULL_BLEED.includes(usePathname());

  if (fullBleed) {
    return (
      <div className="shell shell-full">
        <main className="main main-full">{children}</main>
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">{sidebar}</aside>
      <main className="main">{children}</main>
    </div>
  );
}
