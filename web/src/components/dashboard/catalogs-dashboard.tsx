"use client"

// Catalogs view: the national reference data behind the registries, plus the
// health of the connections that feed it. Every figure here is national — the
// geography and farmer filters do not apply, which is why the sidebar hides
// them while this dashboard is selected.

import { useMemo } from "react"
import {
  AlertTriangle,
  BadgeCheck,
  Ban,
  BookOpen,
  Boxes,
  Cable,
  CircleSlash,
  Cloud,
  Hourglass,
  Layers,
  Leaf,
  Link2,
  MapPinned,
  PawPrint,
  PieChart,
  RefreshCcw,
  ScanLine,
  Sprout,
  TrendingUp,
  Wheat,
} from "lucide-react"
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { useChartGroupData } from "@/hooks/use-chart-group-data"
import { BackToConsoleButton } from "@/components/dashboard/back-to-console-button"
import {
  BRIGHT,
  BRIGHT_SERIES,
  BRIGHT_SOFT,
  CriticalCountChip,
  EmptyPanel,
  FaultAlert,
  FaultBadge,
  ProgressRow,
  REGISTRY_COLORS,
  RegistryCard,
  RegistryDonut,
  RegistryIndicatorTile,
  RegistryStat,
  SEVERITY_TONES,
  SegmentRow,
  type Severity,
  formatCompact,
  formatFull,
} from "@/components/dashboard/registry-ui"
import { toNumber } from "@/components/dashboard/registry-data"
import { ExportDataButton } from "@/components/dashboard/export-button"

/** A row as it comes back from /api/charts, before the panel narrows it. */
type ChartRow = Record<string, unknown>

const CHART_NAMES = [
  "catalogKpis",
  "catalogRegistrySources",
  "catalogIntegrationFaults",
  "catalogExternalIntegrations",
  "catalogCropsByCategory",
  "catalogTopCropsByVariety",
  "catalogVarietyTimeline",
  "catalogVarietySource",
  "catalogBreedsBySpecies",
  "catalogSeedDemandByClass",
  "catalogSeedDemandByCrop",
  "catalogLocationHierarchy",
  "catalogLivestockRegistryStatus",
]

/**
 * Per-catalog accent and glyph, reused across the composition donut, the source
 * list and the external system list so one catalogue always reads the same way.
 */
const REGISTRY_TINTS: Record<string, { color: string; soft: string; icon: React.ReactNode }> = {
  crop: { color: BRIGHT.green, soft: BRIGHT_SOFT.green, icon: <Wheat className="h-3 w-3" /> },
  seed: { color: BRIGHT.amber, soft: BRIGHT_SOFT.amber, icon: <Sprout className="h-3 w-3" /> },
  livestock: { color: BRIGHT.orange, soft: BRIGHT_SOFT.orange, icon: <PawPrint className="h-3 w-3" /> },
  etlits: { color: BRIGHT.violet, soft: BRIGHT_SOFT.violet, icon: <ScanLine className="h-3 w-3" /> },
  location: { color: BRIGHT.blue, soft: BRIGHT_SOFT.blue, icon: <MapPinned className="h-3 w-3" /> },
  catalogue: { color: BRIGHT.tealSoft, soft: BRIGHT_SOFT.teal, icon: <Layers className="h-3 w-3" /> },
}

/** Short, unique slice labels for the composition donut. */
const COMPOSITION_LABELS: Record<string, string> = {
  crop: "Crops",
  seed: "Seed",
  livestock: "Livestock",
  etlits: "ET-LITS",
  location: "Locations",
  catalogue: "Release",
}

/** External systems are grouped by the domain they supply, not by vendor. */
const DOMAIN_ICONS: Record<string, React.ReactNode> = {
  "Crop varieties": <Wheat className="h-3 w-3" />,
  "Livestock species": <PawPrint className="h-3 w-3" />,
  "Livestock records": <ScanLine className="h-3 w-3" />,
  "Breed reference": <BookOpen className="h-3 w-3" />,
  "Admin boundaries": <MapPinned className="h-3 w-3" />,
}

/** Seed classes are multiplication generations, so the glyph tracks the stage. */
const SEED_CLASS_ICONS: Record<string, React.ReactNode> = {
  Breeder: <Sprout className="h-3 w-3" />,
  Basic: <Leaf className="h-3 w-3" />,
  "Certified (C1)": <Wheat className="h-3 w-3" />,
}

/** Breed origin: bred here, imported, or a cross of the two. */
const BREED_TYPE_ICONS: Record<string, React.ReactNode> = {
  Indigenous: <MapPinned className="h-3 w-3" />,
  Exotic: <Cloud className="h-3 w-3" />,
  Cross: <Link2 className="h-3 w-3" />,
}

/**
 * ET-LITS workflow states. The colour carries the meaning — green for records
 * that cleared review, amber for those still in it, red for refusals.
 */
const RECORD_STATUS_STYLES: Record<string, { icon: React.ReactNode; bg: string; color: string }> = {
  Active: { icon: <ScanLine className="h-3.5 w-3.5" />, bg: BRIGHT_SOFT.green, color: BRIGHT.green },
  Approved: { icon: <BadgeCheck className="h-3.5 w-3.5" />, bg: BRIGHT_SOFT.green, color: BRIGHT.greenSoft },
  Pending: { icon: <Hourglass className="h-3.5 w-3.5" />, bg: BRIGHT_SOFT.amber, color: BRIGHT.amber },
  Rework: { icon: <RefreshCcw className="h-3.5 w-3.5" />, bg: BRIGHT_SOFT.orange, color: BRIGHT.orange },
  Rejected: { icon: <Ban className="h-3.5 w-3.5" />, bg: BRIGHT_SOFT.red, color: BRIGHT.crimson },
  Inactive: { icon: <CircleSlash className="h-3.5 w-3.5" />, bg: "#F1F5F9", color: "#64748B" },
}

/** Connection health badge: a registry is degraded once any fault check trips. */
function HealthPill({ faults, connected }: { faults: number; connected: boolean }) {
  const style = !connected
    ? { background: BRIGHT.crimson, color: "#fff", dot: "#fff", label: "Offline" }
    : faults > 0
      ? { background: BRIGHT_SOFT.amber, color: "#92400E", dot: BRIGHT.amber, label: "Degraded" }
      : { background: BRIGHT_SOFT.green, color: "#166534", dot: BRIGHT.green, label: "Healthy" }

  return (
    <span
      className="inline-flex items-center gap-1 whitespace-nowrap rounded-full px-1.5 py-0.5 text-[9.5px] font-bold"
      style={{ background: style.background, color: style.color }}
    >
      <span className="h-1.5 w-1.5 flex-none rounded-full" style={{ background: style.dot }} />
      {style.label}
    </span>
  )
}

export function CatalogsDashboard() {
  // Reference data is national, so the group is fetched with no filters.
  const { data, loading, error } = useChartGroupData(CHART_NAMES)
  const charts = data?.data || {}

  const kpis = charts.catalogKpis?.[0] || null
  const crops = toNumber(kpis?.crops)
  const varieties = toNumber(kpis?.varieties)
  const cropCategories = toNumber(kpis?.crop_categories)
  const seedCrops = toNumber(kpis?.seed_crops)
  const seedYears = toNumber(kpis?.seed_years)
  const species = toNumber(kpis?.species)
  const breeds = toNumber(kpis?.breeds)
  const livestockRecords = toNumber(kpis?.livestock_records)
  const regions = toNumber(kpis?.regions)
  const zones = toNumber(kpis?.zones)
  const woredas = toNumber(kpis?.woredas)

  const sources = useMemo(
    () =>
      (charts.catalogRegistrySources || []).map((row: ChartRow) => {
        const records = toNumber(row.records)
        return {
          key: String(row.registry_key),
          registry: String(row.registry),
          upstream: String(row.upstream),
          detail: String(row.detail || ""),
          records,
          faults: toNumber(row.faults),
          connected: records > 0,
        }
      }),
    [charts.catalogRegistrySources]
  )

  const connectedCount = sources.filter((source) => source.connected).length
  const healthyCount = sources.filter((source) => source.connected && source.faults === 0).length
  const catalogRecords = sources.reduce((acc, source) => acc + source.records, 0)

  // Critical checks lead, then the largest affected populations within each tier.
  const faults = useMemo(
    () =>
      (charts.catalogIntegrationFaults || [])
        .map((row: ChartRow) => ({
          source: String(row.source),
          fault: String(row.fault),
          severity: (String(row.severity) as Severity) || "info",
          records: toNumber(row.records),
        }))
        .filter((row: { records: number }) => row.records > 0)
        .sort((a: { severity: Severity; records: number }, b: { severity: Severity; records: number }) => {
          const rank = SEVERITY_TONES[a.severity].rank - SEVERITY_TONES[b.severity].rank
          return rank !== 0 ? rank : b.records - a.records
        }),
    [charts.catalogIntegrationFaults]
  )

  const criticalFaults = faults.filter((row) => row.severity === "danger")
  const affectedRecords = faults.reduce((acc, row) => acc + row.records, 0)

  const externals = useMemo(
    () =>
      (charts.catalogExternalIntegrations || []).map((row: ChartRow) => ({
        system: String(row.system),
        endpoint: String(row.endpoint),
        domain: String(row.domain),
        linked: toNumber(row.linked_records),
        faults: toNumber(row.faults),
      })),
    [charts.catalogExternalIntegrations]
  )

  const externalsHealthy = externals.filter((row) => row.faults === 0).length

  const compositionSegments = useMemo(
    () =>
      sources
        // The release is a projection of the catalogues above it, so counting
        // it here would count those records twice.
        .filter((source) => source.key !== "catalogue" && source.records > 0)
        .map((source) => ({
          // Keyed off the registry key: trimming the suffix off the display name
          // collapses "Livestock Catalog" and "Livestock Registry" into one slice.
          name: COMPOSITION_LABELS[source.key] || source.registry,
          value: source.records,
          sub: formatCompact(source.records),
          color: REGISTRY_TINTS[source.key]?.color || BRIGHT.blue,
        })),
    [sources]
  )

  const catalogOnlyRecords = compositionSegments.reduce((acc, segment) => acc + segment.value, 0)

  const categorySegments = useMemo(
    () =>
      (charts.catalogCropsByCategory || [])
        .map((row: ChartRow, index: number) => ({
          name: String(row.category),
          value: toNumber(row.crops),
          sub: formatFull(toNumber(row.crops)),
          color:
            String(row.category) === "Uncategorised"
              ? "#CBD5E1"
              : BRIGHT_SERIES[index % BRIGHT_SERIES.length],
        }))
        .filter((segment: { value: number }) => segment.value > 0),
    [charts.catalogCropsByCategory]
  )

  const topCrops = useMemo(
    () =>
      (charts.catalogTopCropsByVariety || []).slice(0, 6).map((row: ChartRow) => ({
        // Catalogue names carry the botanical name in brackets; drop it for the label.
        name: String(row.crop).split("(")[0].trim(),
        value: toNumber(row.varieties),
      })),
    [charts.catalogTopCropsByVariety]
  )

  const topCropMax = topCrops.reduce((acc: number, row: { value: number }) => Math.max(acc, row.value), 0)

  const varietyTimeline = useMemo(
    () =>
      (charts.catalogVarietyTimeline || [])
        .map((row: ChartRow) => ({ year: String(row.year), varieties: toNumber(row.varieties) }))
        .slice(-28),
    [charts.catalogVarietyTimeline]
  )

  const varietySource = useMemo(
    () =>
      (charts.catalogVarietySource || []).map((row: ChartRow) => ({
        name: String(row.source),
        value: toNumber(row.varieties),
      })),
    [charts.catalogVarietySource]
  )

  const domesticVarieties = varietySource.find((row: { name: string }) => row.name === "Domestic")?.value || 0

  const breedRows = useMemo(() => {
    const totals = new Map<string, number>()
    ;(charts.catalogBreedsBySpecies || []).forEach((row: ChartRow) => {
      const key = String(row.breed_type || "Unknown")
      totals.set(key, (totals.get(key) || 0) + toNumber(row.breeds))
    })
    return Array.from(totals.entries())
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [charts.catalogBreedsBySpecies])

  const seedDemandByClass = useMemo(() => {
    const totals = new Map<string, number>()
    ;(charts.catalogSeedDemandByClass || []).forEach((row: ChartRow) => {
      const key = String(row.seed_class)
      totals.set(key, (totals.get(key) || 0) + toNumber(row.quantity_demanded))
    })
    return Array.from(totals.entries())
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [charts.catalogSeedDemandByClass])

  const seedDemandTotal = seedDemandByClass.reduce((acc, row) => acc + row.value, 0)

  const hierarchy = useMemo(
    () =>
      (charts.catalogLocationHierarchy || []).slice(0, 6).map((row: ChartRow) => ({
        name: String(row.region),
        zones: toNumber(row.zones),
        woredas: toNumber(row.woredas),
      })),
    [charts.catalogLocationHierarchy]
  )

  const hierarchyMax = hierarchy.reduce((acc: number, row: { woredas: number }) => Math.max(acc, row.woredas), 0)

  const registryStatus = useMemo(
    () =>
      (charts.catalogLivestockRegistryStatus || []).map((row: ChartRow) => ({
        name: String(row.name),
        records: toNumber(row.records),
        live: Boolean(row.is_live_master_data),
      })),
    [charts.catalogLivestockRegistryStatus]
  )

  const registryStatusTotal = registryStatus.reduce((acc, row) => acc + row.records, 0)

  const categorisedCrops = crops - (categorySegments.find((s: { name: string }) => s.name === "Uncategorised")?.value || 0)
  const cropsWithDemand = seedCrops - (faults.find((f) => f.fault.includes("no demand record"))?.records || 0)
  const breedsInStandard = breeds - (faults.find((f) => f.fault.includes("outside the national standard"))?.records || 0)

  const share = (value: number, total: number) => (total > 0 ? (value / total) * 100 : 0)

  if (error) {
    return (
      <RegistryCard title="Catalogs">
        <div className="px-4 pb-5 pt-3 text-[12px]" style={{ color: REGISTRY_COLORS.red }}>
          Failed to load catalog data: {error}
        </div>
      </RegistryCard>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 @[860px]:grid @[860px]:grid-rows-[auto_minmax(0,182fr)_minmax(0,180fr)_minmax(0,107fr)_auto]">
      {/* Band 1 — catalog scale and connection health */}
      <section className="grid flex-none grid-cols-2 gap-3 @[640px]:grid-cols-3 @[860px]:grid-cols-[1.4fr_1.26fr_1.4fr_1.18fr_1.28fr_1.38fr]">
        <RegistryStat
          icon={<Boxes className="h-7 w-7" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.blue}
          iconColor={BRIGHT.blue}
          tint="blue"
          value={formatCompact(catalogRecords)}
          label="Catalogue Records"
          note={`${sources.length} catalogues and registries`}
          loading={loading}
        />
        <RegistryStat
          icon={<Wheat className="h-7 w-7" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.green}
          iconColor={BRIGHT.green}
          tint="green"
          value={formatFull(crops)}
          label="Crops Catalogued"
          note={`${formatFull(varieties)} released varieties`}
          loading={loading}
        />
        <RegistryStat
          icon={<PawPrint className="h-7 w-7" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.orange}
          iconColor={BRIGHT.orange}
          tint="peach"
          value={formatFull(species)}
          label="Livestock Species"
          note={`${formatFull(breeds)} recognised breeds`}
          loading={loading}
        />
        <RegistryStat
          icon={<MapPinned className="h-7 w-7" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.violet}
          iconColor={BRIGHT.violet}
          tint="violet"
          value={formatFull(woredas)}
          label="Woredas Mapped"
          note={`${formatFull(regions)} regions · ${formatFull(zones)} zones`}
          loading={loading}
        />
        <RegistryStat
          icon={<Cable className="h-7 w-7" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.teal}
          iconColor={BRIGHT.teal}
          tint="teal"
          value={`${connectedCount}/${sources.length}`}
          label="Registries Connected"
          note={`${healthyCount} reporting no faults`}
          loading={loading}
        />
        <RegistryStat
          icon={<AlertTriangle className="h-7 w-7" strokeWidth={2.5} />}
          iconBg={BRIGHT_SOFT.red}
          iconColor={BRIGHT.crimson}
          tint={affectedRecords > 0 ? "red" : "green"}
          value={formatCompact(affectedRecords)}
          valueColor={affectedRecords > 0 ? BRIGHT.crimson : undefined}
          label="Records With Faults"
          note={`${faults.length} checks tripped · ${criticalFaults.length} critical`}
          loading={loading}
        />
      </section>

      {/* Band 2 — connections, composition, crop classification */}
      <section className="grid min-h-0 flex-none grid-cols-1 gap-3 @[720px]:grid-cols-2 @[860px]:grid-cols-[2.9fr_1.9fr_1.9fr_1.7fr]">
        <RegistryCard
          dense
          icon={<Cable className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.teal}
          iconColor={BRIGHT.teal}
          title="Connected Registries"
          subtitle="Sources feeding the catalogues, with live fault checks"
          className="flex min-h-[240px] flex-col overflow-hidden @[860px]:min-h-0"
          bodyClassName="min-h-0 flex-1 overflow-hidden px-3 pb-2 pt-1"
        >
          {sources.length === 0 ? (
            <EmptyPanel message="No registries detected" />
          ) : (
            <div>
              <div
                className="grid grid-cols-[minmax(0,1.35fr)_minmax(0,1.15fr)_58px_52px_auto] gap-2 border-b pb-1 text-[9.5px]"
                style={{ borderColor: REGISTRY_COLORS.line2, color: REGISTRY_COLORS.muted }}
              >
                <span>Registry</span>
                <span>Upstream source</span>
                <span className="text-right">Records</span>
                <span className="text-right">Faults</span>
                <span className="text-right">Status</span>
              </div>
              {sources.map((source) => (
                <div
                  key={source.key}
                  className="grid grid-cols-[minmax(0,1.35fr)_minmax(0,1.15fr)_58px_52px_auto] items-center gap-2 py-[5px] text-[10.5px]"
                  style={{ color: REGISTRY_COLORS.ink2 }}
                >
                  <span className="flex min-w-0 items-center gap-1.5">
                    <span
                      className="grid h-4 w-4 flex-none place-items-center rounded-[5px]"
                      style={{
                        background: REGISTRY_TINTS[source.key]?.soft || BRIGHT_SOFT.blue,
                        color: REGISTRY_TINTS[source.key]?.color || BRIGHT.blue,
                      }}
                    >
                      {REGISTRY_TINTS[source.key]?.icon || <Boxes className="h-3 w-3" />}
                    </span>
                    <span className="min-w-0">
                      <span
                        className="block truncate font-semibold"
                        style={{ color: REGISTRY_COLORS.ink }}
                        title={source.registry}
                      >
                        {source.registry}
                      </span>
                      <span className="block truncate text-[9px]" style={{ color: REGISTRY_COLORS.muted }}>
                        {source.detail}
                      </span>
                    </span>
                  </span>
                  <span className="truncate" title={source.upstream}>
                    {source.upstream}
                  </span>
                  <span className="text-right font-semibold" style={{ color: REGISTRY_COLORS.ink }}>
                    {formatCompact(source.records)}
                  </span>
                  <span className="text-right">
                    <FaultBadge count={source.faults} />
                  </span>
                  <span className="text-right">
                    <HealthPill faults={source.faults} connected={source.connected} />
                  </span>
                </div>
              ))}
            </div>
          )}
        </RegistryCard>

        <RegistryCard
          dense
          icon={<PieChart className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.blue}
          iconColor={BRIGHT.blue}
          title="Catalogue Composition"
          subtitle="Reference records by catalogue"
          className="flex min-h-[220px] flex-col @[860px]:min-h-0"
          bodyClassName="flex min-h-0 flex-1 items-center"
        >
          <RegistryDonut
            subInline
            ringSize={104}
            className="w-full"
            segments={compositionSegments}
            centerValue={formatCompact(catalogOnlyRecords)}
            centerLabel="Records"
            totalLabel="Total"
            totalValue={formatFull(catalogOnlyRecords)}
          />
        </RegistryCard>

        <RegistryCard
          dense
          icon={<Wheat className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.green}
          iconColor={BRIGHT.green}
          title="Crops by Category"
          subtitle={`${formatFull(cropCategories)} categories in the standard`}
          className="flex min-h-[220px] flex-col @[860px]:min-h-0"
          bodyClassName="flex min-h-0 flex-1 items-center"
        >
          <RegistryDonut
            subInline
            ringSize={104}
            className="w-full"
            segments={categorySegments}
            centerValue={formatFull(crops)}
            centerLabel="Crops"
            totalLabel="Classified"
            totalValue={`${formatFull(categorisedCrops)} of ${formatFull(crops)}`}
          />
        </RegistryCard>

        <RegistryCard
          dense
          icon={<Layers className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.violet}
          iconColor={BRIGHT.violet}
          title="Catalogue Completeness"
          className="flex min-h-0 flex-col"
          bodyClassName="grid min-h-0 flex-1 content-start gap-[10px] px-3 pb-2.5 pt-2"
        >
          <SegmentRow
            icon={<Layers className="h-3.5 w-3.5" />}
            iconBg={BRIGHT_SOFT.green}
            iconColor={BRIGHT.green}
            label="Crops with a category"
            value={formatFull(categorisedCrops)}
            share={`(${share(categorisedCrops, crops).toFixed(1)}%)`}
          />
          <SegmentRow
            icon={<Sprout className="h-3.5 w-3.5" />}
            iconBg={BRIGHT_SOFT.amber}
            iconColor={BRIGHT.amber}
            label="Crops with seed demand"
            value={formatFull(cropsWithDemand)}
            share={`(${share(cropsWithDemand, seedCrops).toFixed(1)}%)`}
          />
          <SegmentRow
            icon={<PawPrint className="h-3.5 w-3.5" />}
            iconBg={BRIGHT_SOFT.orange}
            iconColor={BRIGHT.orange}
            label="Breeds in national standard"
            value={formatFull(breedsInStandard)}
            share={`(${share(breedsInStandard, breeds).toFixed(1)}%)`}
          />
          <SegmentRow
            icon={<Leaf className="h-3.5 w-3.5" />}
            iconBg={BRIGHT_SOFT.teal}
            iconColor={BRIGHT.tealSoft}
            label="Domestically bred varieties"
            value={formatFull(domesticVarieties)}
            share={`(${share(domesticVarieties, varieties).toFixed(1)}%)`}
          />
        </RegistryCard>
      </section>

      {/* Band 3 — faults, external systems, variety history, breeding leaders */}
      <section className="grid min-h-0 flex-none grid-cols-1 gap-3 @[720px]:grid-cols-2 @[860px]:grid-cols-[2.35fr_2.6fr_2.2fr_1.85fr]">
        <RegistryCard
          dense
          icon={<AlertTriangle className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.red}
          iconColor={BRIGHT.crimson}
          title="Integration Faults"
          subtitle={`${formatFull(affectedRecords)} records across ${faults.length} failing checks`}
          actions={<CriticalCountChip count={criticalFaults.length} />}
          className="flex min-h-0 flex-col overflow-hidden"
          bodyClassName="grid min-h-0 flex-1 content-start gap-[5px] px-2.5 pb-2 pt-1.5"
        >
          {faults.length === 0 ? (
            <EmptyPanel message="All integrity checks passing" />
          ) : (
            <>
              {faults.slice(0, 5).map((row) => (
                <FaultAlert
                  key={`${row.source}-${row.fault}`}
                  severity={row.severity}
                  title={row.fault}
                  context={row.source}
                  value={formatCompact(row.records)}
                />
              ))}
              {faults.length > 5 && (
                <span className="px-1 text-[9.5px]" style={{ color: REGISTRY_COLORS.muted }}>
                  +{faults.length - 5} further checks tripped
                </span>
              )}
            </>
          )}
        </RegistryCard>

        <RegistryCard
          dense
          icon={<Cloud className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.sky}
          iconColor={BRIGHT.sky}
          title="External Integrations"
          subtitle={`${externals.length} upstream systems · ${externalsHealthy} clean`}
          className="flex min-h-0 flex-col overflow-hidden"
          bodyClassName="min-h-0 flex-1 overflow-hidden px-3 pb-2 pt-1"
        >
          {externals.length === 0 ? (
            <EmptyPanel message="No external systems linked" />
          ) : (
            <div>
              <div
                className="grid grid-cols-[minmax(0,1.5fr)_60px_50px_auto] gap-2 border-b pb-1 text-[9.5px]"
                style={{ borderColor: REGISTRY_COLORS.line2, color: REGISTRY_COLORS.muted }}
              >
                <span>System</span>
                <span className="text-right">Linked</span>
                <span className="text-right">Faults</span>
                <span className="text-right">Status</span>
              </div>
              {externals.map((row) => (
                <div
                  key={row.system}
                  className="grid grid-cols-[minmax(0,1.5fr)_60px_50px_auto] items-center gap-2 py-[5px] text-[10.5px]"
                  style={{ color: REGISTRY_COLORS.ink2 }}
                >
                  <span className="flex min-w-0 items-center gap-1.5">
                    <span
                      className="grid h-4 w-4 flex-none place-items-center rounded-[5px]"
                      style={{ background: BRIGHT_SOFT.sky, color: BRIGHT.sky }}
                    >
                      {DOMAIN_ICONS[row.domain] || <Cloud className="h-3 w-3" />}
                    </span>
                    <span className="min-w-0">
                      <span
                        className="block truncate font-semibold"
                        style={{ color: REGISTRY_COLORS.ink }}
                        title={row.system}
                      >
                        {row.system}
                      </span>
                      <span className="block truncate text-[9px]" style={{ color: REGISTRY_COLORS.muted }}>
                        {row.endpoint} · {row.domain}
                      </span>
                    </span>
                  </span>
                  <span className="text-right font-semibold" style={{ color: REGISTRY_COLORS.ink }}>
                    {formatCompact(row.linked)}
                  </span>
                  <span className="text-right">
                    <FaultBadge count={row.faults} />
                  </span>
                  <span className="text-right">
                    <HealthPill faults={row.faults} connected={row.linked > 0} />
                  </span>
                </div>
              ))}
            </div>
          )}
        </RegistryCard>

        <RegistryCard
          dense
          icon={<TrendingUp className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.green}
          iconColor={BRIGHT.green}
          title="Variety Releases"
          subtitle="Crop varieties released per year"
          className="flex min-h-[200px] flex-col @[860px]:min-h-0"
          bodyClassName="min-h-0 flex-1 px-1 pb-1 pt-1"
        >
          {varietyTimeline.length === 0 ? (
            <EmptyPanel message="No release history" className="px-3 pb-3" />
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={varietyTimeline} margin={{ top: 6, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="catalog-variety-trend" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={BRIGHT.greenSoft} stopOpacity={0.38} />
                    <stop offset="100%" stopColor={BRIGHT.greenSoft} stopOpacity={0.03} />
                  </linearGradient>
                </defs>
                <CartesianGrid vertical={false} stroke={REGISTRY_COLORS.line2} />
                <XAxis
                  dataKey="year"
                  tickLine={false}
                  axisLine={false}
                  interval="preserveStartEnd"
                  minTickGap={26}
                  tick={{ fontSize: 9.5, fill: REGISTRY_COLORS.muted }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  width={28}
                  tick={{ fontSize: 9.5, fill: REGISTRY_COLORS.muted }}
                  tickFormatter={(value: number) => formatCompact(value)}
                />
                <Tooltip
                  contentStyle={{ borderRadius: 10, border: `1px solid ${REGISTRY_COLORS.line}`, fontSize: 11 }}
                  formatter={(value: unknown) => [`${formatFull(toNumber(value))} varieties`, "Released"]}
                />
                <Area
                  type="monotone"
                  dataKey="varieties"
                  stroke={BRIGHT.green}
                  strokeWidth={2}
                  fill="url(#catalog-variety-trend)"
                  dot={{ r: 1.8, fill: "#fff", stroke: BRIGHT.green, strokeWidth: 1.4 }}
                  activeDot={{ r: 3.5, fill: BRIGHT.green, stroke: "#fff", strokeWidth: 1.6 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </RegistryCard>

        <RegistryCard
          dense
          icon={<Wheat className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.lime}
          iconColor={BRIGHT.lime}
          title="Most Improved Crops"
          subtitle="Released varieties per crop"
          className="flex min-h-0 flex-col overflow-hidden"
          bodyClassName="grid min-h-0 flex-1 content-start gap-[7px] px-3 pb-2.5 pt-2"
        >
          {topCrops.length === 0 ? (
            <EmptyPanel message="No variety data" />
          ) : (
            topCrops.map((row: { name: string; value: number }, index: number) => (
              <ProgressRow
                key={row.name}
                icon={<Sprout className="h-3 w-3" />}
                iconColor={BRIGHT_SERIES[index % BRIGHT_SERIES.length]}
                label={row.name}
                value={formatFull(row.value)}
                percent={share(row.value, topCropMax)}
                color={BRIGHT_SERIES[index % BRIGHT_SERIES.length]}
                barWidth="44px"
              />
            ))
          )}
        </RegistryCard>
      </section>

      {/* Band 4 — seed demand, geography, livestock breakdowns */}
      <section className="grid min-h-0 flex-none grid-cols-1 gap-3 @[720px]:grid-cols-2 @[860px]:grid-cols-[2.2fr_2.3fr_2.1fr_2.1fr]">
        <RegistryCard
          dense
          icon={<Sprout className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.amber}
          iconColor={BRIGHT.amber}
          title="Seed Demand by Class"
          subtitle={`${formatCompact(seedDemandTotal)} quintals over ${formatFull(seedYears)} budget years`}
          className="flex min-h-0 flex-col overflow-hidden"
          bodyClassName="grid min-h-0 flex-1 content-start gap-[7px] px-3 pb-2.5 pt-2"
        >
          {seedDemandByClass.length === 0 ? (
            <EmptyPanel message="No seed demand recorded" />
          ) : (
            seedDemandByClass.map((row, index) => (
              <ProgressRow
                key={row.name}
                icon={SEED_CLASS_ICONS[row.name] || <Sprout className="h-3 w-3" />}
                iconColor={BRIGHT_SERIES[index % BRIGHT_SERIES.length]}
                label={row.name}
                value={formatCompact(row.value)}
                percent={share(row.value, seedDemandTotal)}
                color={BRIGHT_SERIES[index % BRIGHT_SERIES.length]}
                barWidth="48px"
              />
            ))
          )}
        </RegistryCard>

        <RegistryCard
          dense
          icon={<MapPinned className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.blue}
          iconColor={BRIGHT.blue}
          title="Administrative Hierarchy"
          subtitle="Woredas per region, joined on P-code"
          className="flex min-h-0 flex-col overflow-hidden"
          bodyClassName="grid min-h-0 flex-1 content-start gap-[7px] px-3 pb-2.5 pt-2"
        >
          {hierarchy.length === 0 ? (
            <EmptyPanel message="No boundary data" />
          ) : (
            hierarchy.map((row: { name: string; zones: number; woredas: number }) => (
              <ProgressRow
                key={row.name}
                icon={<MapPinned className="h-3 w-3" />}
                iconColor={BRIGHT.blue}
                label={`${row.name} · ${row.zones} zones`}
                value={formatFull(row.woredas)}
                percent={share(row.woredas, hierarchyMax)}
                color={BRIGHT.blue}
                barWidth="44px"
              />
            ))
          )}
        </RegistryCard>

        <RegistryCard
          dense
          icon={<PawPrint className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.orange}
          iconColor={BRIGHT.orange}
          title="Breeds by Origin"
          subtitle={`${formatFull(breeds)} breeds across ${formatFull(species)} species`}
          className="flex min-h-0 flex-col overflow-hidden"
          bodyClassName="grid min-h-0 flex-1 content-start gap-[7px] px-3 pb-2.5 pt-2"
        >
          {breedRows.length === 0 ? (
            <EmptyPanel message="No breed data" />
          ) : (
            breedRows.map((row, index) => (
              <ProgressRow
                key={row.name}
                icon={BREED_TYPE_ICONS[row.name] || <PawPrint className="h-3 w-3" />}
                iconColor={BRIGHT_SERIES[index % BRIGHT_SERIES.length]}
                label={row.name}
                value={formatFull(row.value)}
                percent={share(row.value, breeds)}
                color={BRIGHT_SERIES[index % BRIGHT_SERIES.length]}
                barWidth="48px"
              />
            ))
          )}
        </RegistryCard>

        <RegistryCard
          dense
          icon={<ScanLine className="h-3 w-3" />}
          iconBg={BRIGHT_SOFT.violet}
          iconColor={BRIGHT.violet}
          title="ET-LITS Record Status"
          subtitle={`${formatFull(livestockRecords)} animal records`}
          className="flex min-h-0 flex-col"
          bodyClassName="grid min-h-0 flex-1 grid-cols-2 content-center gap-1.5 px-3 pb-2.5 pt-1.5"
        >
          {registryStatusTotal === 0 ? (
            <EmptyPanel message="No registry records" />
          ) : (
            registryStatus
              .filter((row) => row.records > 0)
              .slice(0, 6)
              .map((row) => {
                const style = RECORD_STATUS_STYLES[row.name] || {
                  icon: <Link2 className="h-3.5 w-3.5" />,
                  bg: BRIGHT_SOFT.blue,
                  color: BRIGHT.blue,
                }
                return (
                  <RegistryIndicatorTile
                    key={row.name}
                    icon={style.icon}
                    iconBg={style.bg}
                    iconColor={style.color}
                    value={formatFull(row.records)}
                    label={row.live ? `${row.name} (live)` : row.name}
                  />
                )
              })
          )}
        </RegistryCard>
      </section>

      {/* Source ribbon */}
      <div
        className="flex flex-none items-center gap-2 rounded-xl border px-4 py-1 text-[11px]"
        style={{ borderColor: "#CBE9D6", background: REGISTRY_COLORS.g100, color: REGISTRY_COLORS.g900 }}
      >
        <strong className="font-semibold">Reference data:</strong>
        <span className="min-w-0 flex-1 truncate">
          National catalogues from Ethio-Seed, LIS, ET-LITS and OCHA/HDX, counted live in the catalogue database.
          Every figure is country-wide.
        </span>
        <Leaf className="h-4 w-4 flex-none" style={{ color: REGISTRY_COLORS.g700 }} />
        <BackToConsoleButton />
        <ExportDataButton
          filePrefix="catalogs"
          captureTargetId="dashboard-catalogs"
          csvSections={() => [
            { name: "Connected registries", rows: charts.catalogRegistrySources || [] },
            { name: "Integration faults", rows: charts.catalogIntegrationFaults || [] },
            { name: "External integrations", rows: charts.catalogExternalIntegrations || [] },
            { name: "Crops by category", rows: charts.catalogCropsByCategory || [] },
            { name: "Top crops by variety", rows: charts.catalogTopCropsByVariety || [] },
            { name: "Variety timeline", rows: charts.catalogVarietyTimeline || [] },
            { name: "Variety source", rows: charts.catalogVarietySource || [] },
            { name: "Breeds by species", rows: charts.catalogBreedsBySpecies || [] },
            { name: "Seed demand by class", rows: charts.catalogSeedDemandByClass || [] },
            { name: "Seed demand by crop", rows: charts.catalogSeedDemandByCrop || [] },
            { name: "Location hierarchy", rows: charts.catalogLocationHierarchy || [] },
            { name: "ET-LITS record status", rows: charts.catalogLivestockRegistryStatus || [] },
          ]}
        />
      </div>
    </div>
  )
}
