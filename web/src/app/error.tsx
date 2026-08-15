"use client";

export default function GlobalError({ error, reset }: { error: Error; reset: () => void }) {
  return (
    <div className="errbox" style={{ margin: 24 }}>
      <strong>Something went wrong talking to catalogue-api.</strong>
      <p style={{ margin: "8px 0" }}>{error.message}</p>
      <button className="btn btn-ghost" onClick={reset}>
        Try again
      </button>
    </div>
  );
}
