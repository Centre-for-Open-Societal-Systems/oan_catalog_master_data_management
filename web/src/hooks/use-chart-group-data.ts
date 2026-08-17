"use client";

import { useEffect, useState } from "react";

export interface ChartGroupResult {
  success: boolean;
  data: Record<string, Array<Record<string, unknown>>>;
  errors: Array<{ chart: string; error: string | null }>;
  summary: {
    total: number;
    successful: number;
    failed: number;
    totalExecutionTime: number;
  };
}

interface UseChartGroupResult {
  data: ChartGroupResult | null;
  loading: boolean;
  error: string | null;
}

// Survives remounts within a session so navigating away and back does not
// re-run every query.
const chartGroupCache = new Map<string, ChartGroupResult>();

/** Fetches a set of chart queries in one request to /api/charts. */
export function useChartGroupData(chartNames: string[]): UseChartGroupResult {
  const [data, setData] = useState<ChartGroupResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const chartKey = chartNames.join(",");

  useEffect(() => {
    let cancelled = false;
    const names = chartKey.split(",");

    const fetchCharts = async () => {
      setLoading(true);
      setError(null);

      const cached = chartGroupCache.get(chartKey);
      if (cached) {
        setData(cached);
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`/api/charts?charts=${encodeURIComponent(chartKey)}`);
        if (!response.ok) throw new Error(`HTTP error ${response.status}`);

        const result = await response.json();
        if (!result.success) throw new Error(result.error || "Failed to fetch charts");

        const mapped: ChartGroupResult = {
          success: true,
          data: {},
          errors: [],
          summary: result.summary ?? {
            total: names.length,
            successful: 0,
            failed: 0,
            totalExecutionTime: 0,
          },
        };

        names.forEach((name) => {
          const entry = result.data?.[name];
          mapped.data[name] = entry?.data ?? [];
          if (!entry?.success) {
            mapped.errors.push({ chart: name, error: entry?.error ?? "Unknown error" });
          }
        });

        mapped.summary.successful = names.length - mapped.errors.length;
        mapped.summary.failed = mapped.errors.length;

        if (!cancelled) {
          setData(mapped);
          chartGroupCache.set(chartKey, mapped);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unknown error");
          setData(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    fetchCharts();
    return () => {
      cancelled = true;
    };
  }, [chartKey]);

  return { data, loading, error };
}
