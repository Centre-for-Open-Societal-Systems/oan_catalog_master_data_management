import { CHART_QUERIES } from "@/lib/dashboard/chart-queries";
import { getPool } from "@/lib/dashboard/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type ChartResult = {
  chartName: string;
  success: boolean;
  data: Array<Record<string, unknown>>;
  error: string | null;
  executionTime: number;
};

async function runChart(chartName: string): Promise<ChartResult> {
  const started = Date.now();
  const sql = CHART_QUERIES[chartName];

  if (!sql) {
    return {
      chartName,
      success: false,
      data: [],
      error: `Unknown chart '${chartName}'`,
      executionTime: 0,
    };
  }

  try {
    const result = await getPool().query(sql);
    return {
      chartName,
      success: true,
      data: result.rows,
      error: null,
      executionTime: Date.now() - started,
    };
  } catch (err) {
    return {
      chartName,
      success: false,
      data: [],
      error: err instanceof Error ? err.message : "Unknown database error",
      executionTime: Date.now() - started,
    };
  }
}

export async function GET(request: Request) {
  const requested = new URL(request.url).searchParams.get("charts");
  const chartNames = (requested ? requested.split(",") : Object.keys(CHART_QUERIES))
    .map((name) => name.trim())
    .filter(Boolean);

  if (chartNames.length === 0) {
    return Response.json({ success: false, error: "No charts requested" }, { status: 400 });
  }

  const results = await Promise.all(chartNames.map(runChart));

  const data: Record<string, ChartResult> = {};
  let successful = 0;
  let totalExecutionTime = 0;
  for (const result of results) {
    data[result.chartName] = result;
    totalExecutionTime += result.executionTime;
    if (result.success) successful += 1;
  }

  return Response.json({
    success: true,
    data,
    summary: {
      total: chartNames.length,
      successful,
      failed: chartNames.length - successful,
      totalExecutionTime,
    },
    timestamp: new Date().toISOString(),
  });
}
