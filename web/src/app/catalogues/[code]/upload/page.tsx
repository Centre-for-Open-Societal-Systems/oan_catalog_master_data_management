import Link from "next/link";
import { sectionForCatalogue } from "@/lib/icons";
import { ComingSoon } from "@/components/coming-soon";

export default async function UploadCatalogueValuesPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const section = sectionForCatalogue(code);

  return (
    <ComingSoon
      eyebrow={<><Link href="/catalogues">Catalogues</Link> · <Link href={`/catalogues/${code}`}>{code}</Link> · upload</>}
      title={`Upload ${code} CSV`}
      color={section.color}
      icon={section.icon}
      backHref={`/catalogues/${code}`}
      backLabel={`Back to ${code}`}
      kind="upload"
      bullets={[
        "A file picker accepting CSV, with a downloadable template matching this catalogue's columns",
        "A dry-run preview showing which rows insert, which update an existing code, and which fail validation",
        "Insert/update semantics keyed on code, matching how the seed pipeline already upserts on natural keys",
        "A per-row error report, not an all-or-nothing failure",
      ]}
    />
  );
}
