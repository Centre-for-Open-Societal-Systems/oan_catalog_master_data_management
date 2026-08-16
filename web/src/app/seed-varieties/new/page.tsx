import { SECTION } from "@/lib/icons";
import { ComingSoon } from "@/components/coming-soon";

export default function NewSeedVarietyPage() {
  return (
    <ComingSoon
      eyebrow="Seed Variety · new"
      title="New seed variety"
      color={SECTION.seed.color}
      icon={SECTION.seed.icon}
      backHref="/seed-varieties"
      backLabel="Back to Seed Variety"
      kind="form"
      bullets={[
        "Fields for seed crop, raw crop/variety names, maintainer, classification, and release date",
        "A reconciliation step that attempts to match the entry against the crop variety taxonomy, same as the batch matcher already does",
        "Manual override to confirm or reject a suggested match instead of leaving it Unresolved",
      ]}
    />
  );
}
