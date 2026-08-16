"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { useState } from "react";
import { ICONS } from "@/lib/icons";

type LeafItem = { href: string; label: string };
type SubGroup = { subLabel: string; items: LeafItem[] };
type NavEntry = LeafItem | SubGroup;
type NavGroup = { id: string; label: string; icon: React.ReactNode; items: NavEntry[] };

function isLink(entry: NavEntry): entry is LeafItem {
  return "href" in entry;
}

const GROUPS: NavGroup[] = [
  {
    id: "crop",
    label: "Crop",
    icon: ICONS.crop,
    items: [
      { href: "/catalogues/crop", label: "Crop" },
      { href: "/catalogues/crop_taxonomy_category", label: "Crop Category" },
      // { href: "/catalogues/crop_type", label: "Crop Type" }, // hidden per request — page still works, just not linked in nav
      { href: "/catalogues/crop_variety", label: "Crop Variety" },
      { href: "/catalogues/ecological_zone", label: "Ecological Zone" },
    ],
  },
  {
    id: "livestock",
    label: "Livestock",
    icon: ICONS.livestock,
    items: [
      { href: "/livestock/catalog", label: "Livestock Catalog" },
      { href: "/statistics/livestock-population", label: "Livestock Population" },
      { href: "/livestock/breeds", label: "Livestock Breed" },
      { href: "/livestock/registry-entries", label: "Livestock Registry Entry" },
      {
        subLabel: "References",
        items: [
          { href: "/livestock/genders", label: "Livestock Gender" },
          { href: "/livestock/location-types", label: "Livestock Location Type" },
          { href: "/livestock/body-conditions", label: "Livestock Body Condition" },
          { href: "/livestock/production-types", label: "Livestock Production Type" },
          { href: "/livestock/production-type-species", label: "Livestock Production Type Species" },
          { href: "/livestock/record-statuses", label: "Livestock Record Status" },
        ],
      },
    ],
  },
  {
    id: "geography",
    label: "Geography",
    icon: ICONS.geography,
    items: [
      { href: "/geography?level=region", label: "Region" },
      { href: "/geography?level=zone", label: "Zone" },
      { href: "/geography?level=woreda", label: "Woreda" },
      { href: "/geography?level=kebele", label: "Kebele" },
    ],
  },
  {
    id: "seed",
    label: "Seed",
    icon: ICONS.seed,
    items: [
      { href: "/catalogues/seed_crop", label: "Seed Crop" },
      { href: "/seed-varieties", label: "Seed Variety" },
    ],
  },
  {
    id: "statistics",
    label: "Statistics",
    icon: ICONS.statistics,
    items: [
      { href: "/statistics/livestock-population", label: "Livestock Population" },
      { href: "/statistics/seed-demand-summary", label: "Seed Demand Summary" },
      { href: "/statistics/seed-demand-trends", label: "Seed Demand Trends" },
      { href: "/statistics/seed-demand-by-crop", label: "Seed Demand by Crop" },
    ],
  },
];

const OPERATE: LeafItem[] = [{ href: "/health", label: "Health" }];

function pathOf(href: string) {
  return href.split("?")[0];
}

function flatLinks(items: NavEntry[]): LeafItem[] {
  return items.flatMap((item) => (isLink(item) ? [item] : item.items));
}

function GroupIcon({ children }: { children: React.ReactNode }) {
  return (
    <span className="gi">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round">
        {children}
      </svg>
    </span>
  );
}

function SubGroupNav({ subGroup, currentHref, pathname }: { subGroup: SubGroup; currentHref: string; pathname: string | null }) {
  const [open, setOpen] = useState(() => subGroup.items.some((i) => pathOf(i.href) === pathname));

  return (
    <li>
      <button type="button" className="sub-grp" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
        {subGroup.subLabel}
        <svg className="caret" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
      {open && (
        <ul className="sub sub-nested">
          {subGroup.items.map((item) => (
            <li key={item.href}>
              <Link href={item.href} className={currentHref === item.href ? "on" : undefined} aria-current={currentHref === item.href ? "page" : undefined}>
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

export function NavLinks() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentHref = pathname + (searchParams.toString() ? `?${searchParams.toString()}` : "");

  const [open, setOpen] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    for (const g of GROUPS) initial[g.id] = flatLinks(g.items).some((i) => pathOf(i.href) === pathname);
    return initial;
  });

  return (
    <>
      <p className="nav-label">Browse</p>
      <ul className="nav">
        {GROUPS.map((group) => {
          const isOpen = open[group.id];
          return (
            <li key={group.id}>
              <button
                type="button"
                className="grp"
                aria-expanded={isOpen}
                onClick={() => setOpen((o) => ({ ...o, [group.id]: !o[group.id] }))}
              >
                <GroupIcon>{group.icon}</GroupIcon>
                {group.label}
                <svg className="caret" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m6 9 6 6 6-6" />
                </svg>
              </button>
              {isOpen && (
                <ul className="sub">
                  {group.items.map((item) =>
                    isLink(item) ? (
                      <li key={item.href}>
                        <Link href={item.href} className={currentHref === item.href ? "on" : undefined} aria-current={currentHref === item.href ? "page" : undefined}>
                          {item.label}
                        </Link>
                      </li>
                    ) : (
                      <SubGroupNav key={item.subLabel} subGroup={item} currentHref={currentHref} pathname={pathname} />
                    )
                  )}
                </ul>
              )}
            </li>
          );
        })}
      </ul>

      <p className="nav-label">Operate</p>
      <ul className="nav">
        {OPERATE.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className={`grp${pathname === item.href ? " grp-active" : ""}`}
              style={{ fontWeight: 500, textDecoration: "none" }}
            >
              <GroupIcon>{ICONS.health}</GroupIcon>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
