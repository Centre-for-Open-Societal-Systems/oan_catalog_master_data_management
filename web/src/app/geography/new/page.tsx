import { SECTION } from "@/lib/icons";
import { ComingSoon } from "@/components/coming-soon";

export default function NewGeographyUnitPage() {
  return (
    <ComingSoon
      eyebrow="Geography · new"
      title="New geography unit"
      color={SECTION.geography.color}
      icon={SECTION.geography.icon}
      backHref="/geography"
      backLabel="Back to Geography"
      kind="form"
      bullets={[
        "Level picker (Region / Zone / Woreda / Kebele) and a parent-unit search",
        "Fields for code, display name, Amharic display name, coordinates, and aliases",
        "A duplicate-code check against the active release before saving",
      ]}
    />
  );
}
