import type { CellState } from "@/lib/data/types";

const STYLES: Record<CellState, string> = {
  numeric: "text-slate-900",
  bdl: "border border-slate-300 bg-white italic text-slate-600",
  nd: "border border-slate-300 bg-white italic text-slate-600",
  not_sampled: "hatch border border-slate-300 bg-missing-bg text-slate-600",
  no_table: "hatch border border-dashed border-slate-400 bg-slate-200/60 text-slate-600",
  unknown_flag: "border border-slate-700 bg-white font-semibold text-slate-900",
  invalid_value: "border border-slate-700 bg-white font-semibold text-slate-900",
};

interface Props {
  state: CellState;
  /** Value exactly as printed in the report (numeric, BDL, ND cells). */
  printed?: string;
  /** Short code shown for missing states, e.g. "NS". */
  short: string;
  /** Full description for tooltip and screen readers. */
  title: string;
  compact?: boolean;
}

/**
 * Renders one cell by its state. Numeric readings show the printed value; BDL and ND
 * show their code; not sampled and no table are hatched. No cell is coloured by limits.
 */
export function CellValue({ state, printed, short, title, compact }: Props) {
  const size = compact ? "min-w-[2.5rem] px-1 py-0.5 text-[11px]" : "px-1.5 py-0.5 text-xs";
  const text = state === "numeric" ? printed : state === "bdl" || state === "nd" ? printed || short : short;
  return (
    <span title={title} className={`relative inline-flex items-center justify-center rounded-sm tabular-nums ${size} ${STYLES[state]}`}>
      <span aria-hidden={state !== "numeric"}>{text}</span>
      {state !== "numeric" && <span className="sr-only">{title}</span>}
    </span>
  );
}
