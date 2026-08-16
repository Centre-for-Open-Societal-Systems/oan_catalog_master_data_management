import Link from "next/link";
import { sectionForCatalogue } from "@/lib/icons";
import { ComingSoon } from "@/components/coming-soon";

export default async function NewCatalogueValuePage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  const section = sectionForCatalogue(code);

  return (
    <ComingSoon
      eyebrow={<><Link href="/catalogues">Catalogues</Link> · <Link href={`/catalogues/${code}`}>{code}</Link> · new</>}
      title={`New ${code} value`}
      color={section.color}
      icon={section.icon}
      backHref={`/catalogues/${code}`}
      backLabel={`Back to ${code}`}
      kind="form"
      bullets={[
        "Fields for code, display name, status, sort order, and valid-from/valid-to dates",
        "Parent code picker, for catalogues that are hierarchical",
        "Relation editor, to attach the same typed cross-catalogue links shown on each value's detail page",
        "Server-side validation against the active release before anything is saved",
      ]}
    />
  );
}
