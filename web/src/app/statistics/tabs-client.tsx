"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function TabsClient({ tabs }: { tabs: { href: string; label: string }[] }) {
  const pathname = usePathname();
  return (
    <div className="tabs">
      {tabs.map((t) => (
        <Link key={t.href} href={t.href} className={pathname === t.href ? "on" : undefined}>
          {t.label}
        </Link>
      ))}
    </div>
  );
}
