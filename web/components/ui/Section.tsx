import type { ReactNode } from "react";

interface Props {
  id?: string;
  title?: string;
  subtitle?: string;
  aside?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Section({ id, title, subtitle, aside, children, className = "" }: Props) {
  const headingId = id ? `${id}-heading` : undefined;
  return (
    <section
      id={id}
      aria-labelledby={headingId}
      className={`print-break-avoid scroll-mt-4 rounded-md border border-slate-200 bg-white ${className}`}
    >
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-slate-200 px-4 py-3">
        <div className="min-w-0">
          {title && (
            <h2 id={headingId} className="text-base font-semibold text-slate-900">
              {title}
            </h2>
          )}
          {subtitle && <p className="mt-0.5 max-w-3xl text-xs text-slate-600">{subtitle}</p>}
        </div>
        {aside && <div className="shrink-0">{aside}</div>}
      </div>
      <div className="px-4 py-3">{children}</div>
    </section>
  );
}
