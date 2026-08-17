// Shared data shaping for the dashboard panels.

export function toNumber(value: unknown): number {
  const parsed = typeof value === "number" ? value : parseFloat(String(value ?? 0));
  return Number.isFinite(parsed) ? parsed : 0;
}
