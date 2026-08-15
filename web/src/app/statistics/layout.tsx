import { TabsClient } from "./tabs-client";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";

const TABS = [
  { href: "/statistics/livestock-population", label: "Livestock population" },
  { href: "/statistics/seed-demand-summary", label: "Seed demand summary" },
  { href: "/statistics/seed-demand-trends", label: "Seed demand trends" },
  { href: "/statistics/seed-demand-by-crop", label: "Seed demand by crop" },
];

export default function StatisticsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ "--section-color": SECTION.statistics.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Statistics"
        subtitle="Derived series from the seeded release, fetched live from the four statistics endpoints."
        color={SECTION.statistics.color}
        icon={SECTION.statistics.icon}
      />
      <TabsClient tabs={TABS} />
      {children}
    </div>
  );
}
