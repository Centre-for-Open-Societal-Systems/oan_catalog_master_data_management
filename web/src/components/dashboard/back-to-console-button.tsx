"use client";

import { ArrowLeft } from "lucide-react";
import { useRouter } from "next/navigation";

import { REGISTRY_COLORS } from "@/components/dashboard/registry-ui";

const FALLBACK = "/catalogues";

/**
 * Returns to the page the dashboard was opened from. The opener passes it as
 * `?from=`; a direct visit has nothing to go back to and lands on the
 * catalogue list instead.
 *
 * Reads the query from `window.location` rather than `useSearchParams`, so
 * this control cannot suspend the surrounding dashboard (which would leave
 * every panel empty while the search-params promise was pending).
 *
 * Styled to match ExportDataButton's default tone, since the two sit together
 * in the ribbon, and marked as an export control so it is left out of the
 * image and PDF captures.
 */
export function BackToConsoleButton() {
  const router = useRouter();

  return (
    <button
      type="button"
      data-export-control="true"
      onClick={() => {
        const from = new URLSearchParams(window.location.search).get("from");
        const target = from && from.startsWith("/") && !from.startsWith("//") ? from : FALLBACK;
        router.push(target);
      }}
      title="Back to the catalogue console"
      className="inline-flex flex-none items-center gap-1 rounded-md border bg-white px-2 py-[3px] text-[10px] font-semibold outline-none transition-colors hover:bg-[#F2F8F4]"
      style={{ borderColor: REGISTRY_COLORS.line, color: REGISTRY_COLORS.g700 }}
    >
      <ArrowLeft className="h-3 w-3" />
      Back
    </button>
  );
}
