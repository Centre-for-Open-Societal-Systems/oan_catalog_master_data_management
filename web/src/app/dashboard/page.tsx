import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";

import { CatalogsDashboard } from "@/components/dashboard/catalogs-dashboard";
import "./dashboard.css";

export const metadata: Metadata = {
  title: "Catalogue Dashboard",
  description: "Scale, composition and connection health of the national reference data",
};

// The panels read live counts on every visit.
export const dynamic = "force-dynamic";

export default function DashboardPage() {
  return (
    <div className={`dash-root ${GeistSans.className}`}>
      {/* Capture target for the export button, and the height the panel grid
          divides between its bands. */}
      <div id="dashboard-catalogs" className="h-full min-h-0">
        <CatalogsDashboard />
      </div>
    </div>
  );
}
