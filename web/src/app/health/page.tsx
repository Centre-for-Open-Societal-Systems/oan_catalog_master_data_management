import { getCurrentRelease, getHealthReady } from "@/lib/api";
import { SECTION } from "@/lib/icons";
import { SectionHeader } from "@/components/section-header";

export default async function HealthPage() {
  let ready: Awaited<ReturnType<typeof getHealthReady>> | null = null;
  let readyError: string | null = null;
  try {
    ready = await getHealthReady();
  } catch (err) {
    readyError = err instanceof Error ? err.message : "unknown error";
  }

  let release: Awaited<ReturnType<typeof getCurrentRelease>> | null = null;
  try {
    release = await getCurrentRelease();
  } catch {
    // surfaced via layout banner already
  }

  const dbOk = ready?.checks.database === "up";
  const schemaOk = ready?.checks.schema === "current";

  return (
    <div style={{ "--section-color": SECTION.health.color } as React.CSSProperties}>
      <SectionHeader
        eyebrow="Operate"
        title="Health"
        subtitle={
          <>
            Live from <code className="mono">GET /health/ready</code> and{" "}
            <code className="mono">GET /v1/releases/current</code>.
          </>
        }
        color={SECTION.health.color}
        icon={SECTION.health.icon}
      />

      {readyError ? (
        <div className="errbox">Could not reach /health/ready: {readyError}</div>
      ) : (
        <div className="tiles">
          <div className={`tile ${ready?.status === "ready" ? "ok" : "bad"}`}>
            <div className="tile-k">Readiness</div>
            <div className="tile-v">{ready?.status.toUpperCase()}</div>
          </div>
          <div className={`tile ${dbOk ? "ok" : "bad"}`}>
            <div className="tile-k">Database</div>
            <div className="tile-v">{ready?.checks.database.toUpperCase()}</div>
          </div>
          <div className={`tile ${schemaOk ? "ok" : "warn"}`}>
            <div className="tile-k">Schema</div>
            <div className="tile-v">{ready?.checks.schema.toUpperCase()}</div>
            <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 4 }}>
              {ready?.schema_version} (expected {ready?.expected_schema_version})
            </div>
          </div>
          {release && (
            <div className="tile ok">
              <div className="tile-k">Active release</div>
              <div className="tile-v" style={{ fontSize: 15 }}>{release.version}</div>
              <div style={{ fontSize: 11, color: "var(--ink-3)", marginTop: 4 }}>
                activated {new Date(release.activated_at).toLocaleString()}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
