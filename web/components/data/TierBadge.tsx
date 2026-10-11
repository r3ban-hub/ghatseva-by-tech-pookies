import type { Tier } from "@/lib/data/types";

const STYLES: Record<Tier, string> = {
  1: "border-risk-red-line bg-risk-red-bg text-risk-red",
  2: "border-risk-amber-line bg-risk-amber-bg text-risk-amber",
  3: "border-slate-300 bg-slate-100 text-slate-700",
  4: "border-slate-300 bg-white text-slate-600",
};

export function TierBadge({ tier, label, title }: { tier: Tier; label: string; title?: string }) {
  return (
    <span
      title={title}
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-semibold whitespace-nowrap ${STYLES[tier]}`}
    >
      {label}
    </span>
  );
}
