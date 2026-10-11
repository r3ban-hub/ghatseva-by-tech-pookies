import type { CellState, GridCell } from "@/lib/data/types";

export type StateCounts = Record<CellState, number> & { expected: number };

/** Counts grid cells by display state (coverage bookkeeping only; no limit comparisons). */
export function countStates(cells: GridCell[], parameter?: string): StateCounts {
  const counts: StateCounts = { numeric: 0, bdl: 0, nd: 0, not_sampled: 0, no_table: 0, unknown_flag: 0, invalid_value: 0, expected: 0 };
  for (const c of cells) {
    if (parameter && c.parameter !== parameter) continue;
    counts[c.state] += 1;
    counts.expected += 1;
  }
  return counts;
}

export const KEY_PARAMETERS = ["Dissolved oxygen", "BOD", "pH"] as const;

/** True when the backend compared this reading with its Class B limit (pass or fail). */
export function isUsable(c: GridCell): boolean {
  if (!c.reading || c.reading.value === null) return false;
  return c.reading.classB !== undefined ? c.reading.classB === "pass" || c.reading.classB === "fail" : c.state === "numeric";
}

/** A DO / BOD / pH cell with no usable number: no table, not sampled, BDL/ND, unresolved, invalid or contradictory. */
export function isGap(c: GridCell): boolean {
  return !isUsable(c);
}
