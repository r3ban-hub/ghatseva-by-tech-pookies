import type { Fraction } from "@/lib/data/types";

interface Props {
  value: Fraction;
  text: string;
  /** Accessible description, e.g. "11 of 13 numeric readings". */
  label?: string;
  width?: string;
}

/** "n/N" with a small proportion bar. The bar only visualises the supplied fraction. */
export function FractionBar({ value, text, label, width = "w-16" }: Props) {
  const pct = value.N > 0 ? (value.n / value.N) * 100 : 0;
  return (
    <span className="inline-flex items-center gap-2" title={label}>
      <span className="min-w-[3.25rem] text-right font-medium text-slate-900 tabular-nums">{text}</span>
      <span aria-hidden className={`relative h-1.5 ${width} overflow-hidden rounded-full bg-slate-200`}>
        <span className="absolute inset-y-0 left-0 rounded-full bg-navy" style={{ width: `${pct}%` }} />
      </span>
      {label && <span className="sr-only">{label}</span>}
    </span>
  );
}
