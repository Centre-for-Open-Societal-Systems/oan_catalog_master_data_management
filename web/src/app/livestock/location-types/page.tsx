import Link from "next/link";
import { getLivestockReferenceData } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";
import { TableExport } from "@/components/table-export";

export default async function LivestockLocationTypesPage() {
  const { location_types } = await getLivestockReferenceData();

  return (
    <div style={{ "--section-color": SECTION.livestock.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Browse"
        title="Livestock Location Type"
        subtitle={
          <>
            Grazing-area bands, each resolved to an ecological zone. Fetched live from{" "}
            <code className="mono">GET /v1/livestock/reference-data</code>.
          </>
        }
        color={SECTION.livestock.color}
        icon={SECTION.livestock.icon}
      />

      <div className="dt-card">
        <div className="dt-toolbar">
          <span className="dt-count">{location_types.length} location types</span>
          <TableExport
            headers={["Code", "Ethiopian zone", "Ecological zone", "Altitude", "Description"]}
            rows={location_types.map((l) => [
              l.code,
              l.ethiopian_zone_name ?? "",
              l.ecological_zone.display_name,
              l.altitude_description ?? "",
              l.description ?? "",
            ])}
            filename="livestock_location_types"
          />
        </div>
        <div className="table-wrap">
          <table className="dt">
            <thead>
              <tr>
                <th style={{ width: 130 }}>Code</th>
                <th style={{ width: 140 }}>Ethiopian zone</th>
                <th style={{ width: 160 }}>Ecological zone</th>
                <th style={{ width: 220 }}>Altitude</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {location_types.map((l) => (
                <tr key={l.code}>
                  <td><span className="dt-code">{l.code}</span></td>
                  <td className="dt-name">{l.ethiopian_zone_name ?? "—"}</td>
                  <td>
                    <Link className="chip" href={`/catalogues/ecological_zone/${encodeURIComponent(l.ecological_zone.code)}`}>
                      <span className="v">{l.ecological_zone.display_name}</span>
                    </Link>
                  </td>
                  <td className="dt-dim">{l.altitude_description ?? "—"}</td>
                  <td className="dt-dim">{l.description ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
