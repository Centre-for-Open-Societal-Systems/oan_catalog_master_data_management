import { SECTION } from "@/lib/icons";
import { ComingSoon } from "@/components/coming-soon";

export default function UploadSeedVarietiesPage() {
  return (
    <ComingSoon
      eyebrow="Seed Variety · upload"
      title="Upload seed variety CSV"
      color={SECTION.seed.color}
      icon={SECTION.seed.icon}
      backHref="/seed-varieties"
      backLabel="Back to Seed Variety"
      kind="upload"
      bullets={[
        "Bulk import of registry rows in the Ethiopia Seed System's own column shape",
        "Automatic reconciliation against the crop variety taxonomy for every uploaded row, reporting Matched/Unresolved/Conflict before commit",
        "Insert/update keyed on the registry's source variety ID",
      ]}
    />
  );
}
