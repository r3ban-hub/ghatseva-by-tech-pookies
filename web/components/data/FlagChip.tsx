import { AlertTriangle, CircleDashed, HelpCircle } from "lucide-react";
import type { FlagSeverity } from "@/lib/data/types";

const STYLES: Record<FlagSeverity, string> = {
  red: "border-risk-red-line bg-risk-red-bg text-risk-red",
  amber: "border-risk-amber-line bg-risk-amber-bg text-risk-amber",
  neutral: "hatch border-slate-300 bg-missing-bg text-slate-700",
};

interface Props {
  severity: FlagSeverity;
  label: string;
  title?: string;
  identity?: boolean;
}

/** Colour is never the only signal: every chip carries an icon and text. */
export function FlagChip({ severity, label, title, identity }: Props) {
  const Icon = severity === "neutral" ? (identity ? HelpCircle : CircleDashed) : AlertTriangle;
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap ${STYLES[severity]}`}
    >
      <Icon aria-hidden className="h-3 w-3" />
      {label}
    </span>
  );
}
