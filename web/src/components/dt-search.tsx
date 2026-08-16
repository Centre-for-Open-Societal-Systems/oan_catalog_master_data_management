export function DtSearch({ name, defaultValue, placeholder }: { name: string; defaultValue?: string; placeholder: string }) {
  return (
    <div className="dt-search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <circle cx="11" cy="11" r="7" />
        <path d="m20 20-3.5-3.5" />
      </svg>
      <input type="search" name={name} defaultValue={defaultValue} placeholder={placeholder} aria-label={placeholder} />
    </div>
  );
}
