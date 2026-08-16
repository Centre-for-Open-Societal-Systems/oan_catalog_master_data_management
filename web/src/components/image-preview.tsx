"use client";

import { useState } from "react";

export function ImagePreview({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);

  if (failed) {
    return (
      <a className="btn btn-ghost" href={src} target="_blank" rel="noreferrer">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
          <path d="M15 3h6v6M10 14 21 3" />
        </svg>
        Open image in new tab
      </a>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element -- external, unpredictable host; next/image optimization isn't worth configuring for it
    <img
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
      style={{ maxWidth: "100%", maxHeight: 320, borderRadius: 8, border: "1px solid var(--line)", display: "block" }}
    />
  );
}
