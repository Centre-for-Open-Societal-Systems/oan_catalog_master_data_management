import { SECTION } from "@/lib/icons";
import { ComingSoon } from "@/components/coming-soon";

export default function UploadGeographyPage() {
  return (
    <ComingSoon
      eyebrow="Geography · upload"
      title="Upload geography CSV"
      color={SECTION.geography.color}
      icon={SECTION.geography.icon}
      backHref="/geography"
      backLabel="Back to Geography"
      kind="upload"
      bullets={[
        "One file per level, or a single file with a level column",
        "Parent-code resolution against already-published units, with a clear report of any that don't resolve — the same MISSING_PARENT handling the real pipeline already does for a handful of woredas",
        "A dry-run preview before anything commits",
      ]}
    />
  );
}
