import { Pool } from "pg";

/**
 * Read-only pool for the dashboard panels. The rest of the console goes through
 * catalogue-api; the dashboard aggregates across the staging tables, which the
 * read API does not expose, so it queries the catalogue database directly.
 *
 * Defaults match compose.yaml as published to the host.
 */
const globalForPool = globalThis as unknown as { cataloguePool?: Pool };

export function getPool(): Pool {
  if (!globalForPool.cataloguePool) {
    globalForPool.cataloguePool = new Pool({
      host: process.env.CATALOGUE_DB_HOST ?? "localhost",
      port: Number(process.env.CATALOGUE_DB_PORT ?? 55432),
      database: process.env.CATALOGUE_DB ?? "catalogue",
      user: process.env.CATALOGUE_DB_USER ?? "catalogue",
      password: process.env.CATALOGUE_DB_PASSWORD ?? "catalogue",
      max: 8,
      idleTimeoutMillis: 30_000,
      connectionTimeoutMillis: 5_000,
    });
  }
  return globalForPool.cataloguePool;
}
