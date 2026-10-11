import type { GridCell } from "@/lib/data/types";
import type { Dictionary } from "@/lib/i18n";
import { paramName, refStatus, refText, seasonLabel } from "@/lib/format";
import { SourceRefLink } from "@/components/data/SourceRefLink";
import { CellValue } from "./CellValue";

export function cellTitle(cell: GridCell, t: Dictionary): string {
  const base = t.valueState[cell.state];
  if (cell.state === "no_table") {
    return `${base}: ${cell.missingReason === "season_table_absent" ? t.ghat.coverage.seasonAbsent : t.ghat.coverage.paramAbsent}`;
  }
  if (cell.state === "unknown_flag" && cell.reading) return `${base}: “${cell.reading.flag}”`;
  if (cell.state === "numeric" && cell.reading) {
    const unit = cell.reading.unitAssumed ? ` ${cell.reading.unitAssumed}` : "";
    return `${cell.reading.valueAsPrinted}${unit}`;
  }
  return base;
}

/** Compact list of grid cells used inside expandable reasons. */
export function ReadingMiniTable({ cells, t, showParameter }: { cells: GridCell[]; t: Dictionary; showParameter?: boolean }) {
  const e = t.ghat.evidence.col;
  return (
    <div className="relative overflow-x-auto">
      <table className="mt-2 w-auto min-w-[420px] text-xs">
        <thead className="text-left text-slate-500">
          <tr className="border-b border-slate-200">
            <th scope="col" className="py-1 pr-3 font-medium">{e.season}</th>
            <th scope="col" className="py-1 pr-3 font-medium">{e.phase}</th>
            {showParameter && <th scope="col" className="py-1 pr-3 font-medium">{e.parameter}</th>}
            <th scope="col" className="py-1 pr-3 font-medium">{e.value}</th>
            <th scope="col" className="py-1 font-medium">{e.source}</th>
          </tr>
        </thead>
        <tbody>
          {cells.map((c) => (
            <tr key={c.key} className="border-b border-slate-100 last:border-0">
              <td className="py-1 pr-3 whitespace-nowrap">{seasonLabel(c, t)}</td>
              <td className="py-1 pr-3 whitespace-nowrap">{t.phaseShort[c.phase]}</td>
              {showParameter && <td className="py-1 pr-3 whitespace-nowrap">{paramName(c.parameter, t)}</td>}
              <td className="py-1 pr-3">
                <CellValue
                  state={c.state}
                  printed={c.reading?.valueAsPrinted}
                  short={t.valueStateShort[c.state]}
                  title={cellTitle(c, t)}
                  compact
                />
                {c.state === "numeric" && c.reading?.unitAssumed && (
                  <span className="ml-1 text-[11px] text-slate-500">{c.reading.unitAssumed}</span>
                )}
              </td>
              <td className="py-1">
                {c.reading?.source ? (
                  <SourceRefLink source={c.reading.source} text={refText(c.reading.source, t)} statusText={refStatus(c.reading.source, t)} />
                ) : (
                  <span className="text-[11px] text-slate-400">{t.ghat.evidence.noPage}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
