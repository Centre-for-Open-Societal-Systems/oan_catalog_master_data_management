import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Suspense } from "react";
import "./globals.css";
import { getCurrentRelease } from "@/lib/api";
import { AppShell } from "@/components/app-shell";
import { DashboardLink } from "@/components/dashboard-link";
import { NavLinks } from "@/components/nav-links";
import { ThemeToggle } from "@/components/theme-toggle";

export const metadata: Metadata = {
  title: "Catalogue Console",
  description: "Reference data browser for the OpenG2P catalogue-service",
};

const NO_FLASH_THEME_SCRIPT = `
try {
  var t = localStorage.getItem('theme');
  if (t === 'dark' || t === 'light') document.documentElement.setAttribute('data-theme', t);
} catch (e) {}
`;

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  let release: Awaited<ReturnType<typeof getCurrentRelease>> | null = null;
  let releaseError: string | null = null;
  try {
    release = await getCurrentRelease();
  } catch (err) {
    releaseError = err instanceof Error ? err.message : "unknown error";
  }

  return (
    <html lang="en">
      <head>
        <script dangerouslySetInnerHTML={{ __html: NO_FLASH_THEME_SCRIPT }} />
      </head>
      <body>
        <header className="topbar">
          <Link className="brand" href="/catalogues">
            <span className="brand-mark">
              <Image src="/images/ati_logo.png" alt="ATI" width={24} height={21} priority style={{ objectFit: "contain" }} />
            </span>
            <span className="brand-name">
              Catalogue Console
              <span>reference data · live</span>
            </span>
          </Link>

          <div className="topbar-end">
            <Suspense fallback={null}>
              <DashboardLink />
            </Suspense>

            {release ? (
              <div className="stamp" title="Release every figure on this page was resolved against">
                <div>
                  <b>Country</b>
                  <span className="v">{release.country_code}</span>
                </div>
                <div>
                  <b>Release</b>
                  <span className="v">{release.version}</span>
                </div>
              </div>
            ) : (
              <span className="badge bad">API unreachable</span>
            )}
          </div>

          <ThemeToggle />
        </header>

        {releaseError && (
          <div className="hint" style={{ margin: "12px 24px", borderColor: "var(--brick)" }}>
            <span>
              Could not load the active release: {releaseError}. Start the API with{" "}
              <code>docker compose up</code> in <code>catalogue-service/</code>.
            </span>
          </div>
        )}

        <AppShell
          sidebar={
            <>
              <Suspense fallback={null}>
                <NavLinks />
              </Suspense>

              <div className="side-foot">
                <span className="avatar">•</span>
                <span className="who">
                  {release ? `${release.country_code} · ${release.status}` : "not connected"}
                  <span>dev · unauthenticated</span>
                </span>
              </div>
            </>
          }
        >
          {children}
        </AppShell>
      </body>
    </html>
  );
}
