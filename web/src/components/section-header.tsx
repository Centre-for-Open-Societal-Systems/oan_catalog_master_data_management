import type { CSSProperties, ReactNode } from "react";

export function SectionHeader({
  eyebrow,
  title,
  subtitle,
  color,
  icon,
  meta,
}: {
  eyebrow: ReactNode;
  title: ReactNode;
  subtitle?: ReactNode;
  color: string;
  icon: ReactNode;
  meta?: ReactNode;
}) {
  return (
    <div className="pagehead" style={{ "--section-color": color } as CSSProperties}>
      <div className="pagehead-main">
        <span className="pagehead-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
            {icon}
          </svg>
        </span>
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="title">{title}</h1>
          {subtitle && <p className="subtitle">{subtitle}</p>}
        </div>
      </div>
      {meta && <div className="head-meta">{meta}</div>}
    </div>
  );
}
