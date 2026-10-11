export interface CoverageItem {
  param: string;
  numeric: number;
  expected: number;
  title: string;
}

/** Numeric readings out of expected cells per parameter. The missing part is hatched, never filled. */
export function CoverageMeter({ items }: { items: CoverageItem[] }) {
  return (
    <span className="inline-flex flex-col gap-1">
      {items.map((it) => {
        const pct = it.expected > 0 ? (it.numeric / it.expected) * 100 : 0;
        const complete = it.numeric === it.expected;
        return (
          <span key={it.param} className="inline-flex items-center gap-1.5 text-[11px]" title={it.title}>
            <span className="w-7 text-slate-500">{it.param}</span>
            <span aria-hidden className="hatch relative h-2 w-10 overflow-hidden rounded-sm border border-slate-300 bg-white">
              <span className="absolute inset-y-0 left-0 bg-slate-500" style={{ width: `${pct}%` }} />
            </span>
            <span className={`tabular-nums ${complete ? "text-slate-600" : "font-semibold text-slate-900"}`}>
              {it.numeric}/{it.expected}
            </span>
            <span className="sr-only">{it.title}</span>
          </span>
        );
      })}
    </span>
  );
}
