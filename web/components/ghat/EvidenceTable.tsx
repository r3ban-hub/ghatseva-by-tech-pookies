"use client";

import { useMemo, useState, type ChangeEvent } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, RotateCcw } from "lucide-react";
import type { CellState, Festival, Phase, SourceRef } from "@/lib/data/types";
import { SourceRefLink } from "@/components/data/SourceRefLink";
import { CellValue } from "./CellValue";

/** One evidence row, prepared on the server. The table filters and sorts; it never evaluates readings. */
export interface EvidenceRowView {
  key: string;
  seasonIdx: number;
  year: number;
  festival: Festival;
  seasonText: string;
  phase: Phase;
  phaseIdx: number;
  phaseText: string;
  parameter: string;
  paramIdx: number;
  paramText: string;
  isKey: boolean;
  parameterAsPrinted: string | null;
  valueAsPrinted: string | null;
  value: number | null;
  unit: string;
  state: CellState;
  stateText: string;
  short: string;
  cellTitle: string;
  rawFlag: string | null;
  criterion: string;
  siteAsPrinted: string | null;
  source: SourceRef | null;
  sourceText: string | null;
  sourceStatus: string | null;
  csvLine: number | null;
}

export interface EvidenceLabels {
  filters: {
    label: string;
    year: string;
    festival: string;
    phase: string;
    parameter: string;
    state: string;
    all: string;
    keyParams: string;
    allParams: string;
    readings: string;
    missing: string;
    reset: string;
  };
  col: Record<
    "season" | "phase" | "parameter" | "printedAs" | "value" | "unit" | "state" | "criterion" | "siteAsPrinted" | "source" | "csvLine",
    string
  >;
  showing: string;
  empty: string;
  noRow: string;
  noPage: string;
  flagLabel: string;
  festivals: Record<Festival, string>;
  phases: Record<Phase, string>;
  parameters: { value: string; text: string }[];
}

type SortKey = "season" | "phase" | "parameter" | "value";
const READING_STATES = new Set<CellState>(["numeric", "bdl", "nd"]);
const DEFAULT_FILTERS = { year: "all", festival: "all", phase: "all", parameter: "key", state: "all" };

export function EvidenceTable({ rows, labels }: { rows: EvidenceRowView[]; labels: EvidenceLabels }) {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "season", dir: "asc" });
  const f = labels.filters;

  const visible = useMemo(() => {
    const out = rows.filter(
      (r) =>
        (filters.year === "all" || String(r.year) === filters.year) &&
        (filters.festival === "all" || r.festival === filters.festival) &&
        (filters.phase === "all" || r.phase === filters.phase) &&
        (filters.parameter === "all" || (filters.parameter === "key" ? r.isKey : r.parameter === filters.parameter)) &&
        (filters.state === "all" || (filters.state === "readings" ? READING_STATES.has(r.state) : !READING_STATES.has(r.state))),
    );
    const natural = (a: EvidenceRowView, b: EvidenceRowView) =>
      a.seasonIdx - b.seasonIdx || a.paramIdx - b.paramIdx || a.phaseIdx - b.phaseIdx;
    const dir = sort.dir === "asc" ? 1 : -1;
    return out.sort((a, b) => {
      switch (sort.key) {
        case "season":
          return dir * (a.seasonIdx - b.seasonIdx) || natural(a, b);
        case "phase":
          return dir * (a.phaseIdx - b.phaseIdx) || natural(a, b);
        case "parameter":
          return dir * (a.paramIdx - b.paramIdx) || natural(a, b);
        case "value":
          // Cells without a number always sort last, whatever the direction.
          if (a.value === null && b.value === null) return natural(a, b);
          if (a.value === null) return 1;
          if (b.value === null) return -1;
          return dir * (a.value - b.value) || natural(a, b);
      }
    });
  }, [rows, filters, sort]);

  const set = (key: keyof typeof DEFAULT_FILTERS) => (e: ChangeEvent<HTMLSelectElement>) =>
    setFilters((prev) => ({ ...prev, [key]: e.target.value }));

  const toggle = (key: SortKey) => setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }));

  const sortHeader = (key: SortKey, text: string) => {
    const active = sort.key === key;
    const Icon = !active ? ArrowUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown;
    return (
      <th scope="col" aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"} className="px-2 py-2 text-left font-medium whitespace-nowrap">
        <button type="button" onClick={() => toggle(key)} className="inline-flex items-center gap-1 rounded px-1 py-0.5 hover:bg-slate-200/70 hover:text-slate-900">
          {text}
          <Icon aria-hidden className={`h-3 w-3 ${active ? "text-navy" : "text-slate-400"}`} />
        </button>
      </th>
    );
  };

  const plainHeader = (text: string) => (
    <th scope="col" className="px-2 py-2 text-left font-medium whitespace-nowrap">
      {text}
    </th>
  );

  const select = (id: keyof typeof DEFAULT_FILTERS, label: string, options: { value: string; text: string }[]) => (
    <label className="flex flex-col gap-0.5 text-[11px] font-medium text-slate-600">
      {label}
      <select
        value={filters[id]}
        onChange={set(id)}
        className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800 hover:border-slate-400 focus:border-accent"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.text}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div>
      <fieldset className="no-print mb-3 flex flex-wrap items-end gap-3">
        <legend className="sr-only">{f.label}</legend>
        {select("year", f.year, [{ value: "all", text: f.all }, ...["2023", "2024", "2025"].map((y) => ({ value: y, text: y }))])}
        {select("festival", f.festival, [
          { value: "all", text: f.all },
          { value: "Ganesh", text: labels.festivals.Ganesh },
          { value: "Durga", text: labels.festivals.Durga },
        ])}
        {select("phase", f.phase, [
          { value: "all", text: f.all },
          ...(["pre", "during", "after"] as Phase[]).map((p) => ({ value: p, text: labels.phases[p] })),
        ])}
        {select("parameter", f.parameter, [
          { value: "key", text: f.keyParams },
          { value: "all", text: f.allParams },
          ...labels.parameters,
        ])}
        {select("state", f.state, [
          { value: "all", text: f.all },
          { value: "readings", text: f.readings },
          { value: "missing", text: f.missing },
        ])}
        <button
          type="button"
          onClick={() => setFilters(DEFAULT_FILTERS)}
          className="inline-flex items-center gap-1 rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 hover:border-navy hover:text-navy"
        >
          <RotateCcw aria-hidden className="h-3 w-3" />
          {f.reset}
        </button>
        <p className="ml-auto text-xs text-slate-500" aria-live="polite">
          {labels.showing.replace("{n}", String(visible.length)).replace("{N}", String(rows.length))}
        </p>
      </fieldset>

      <div className="relative max-h-[36rem] overflow-auto rounded border border-slate-200 print:max-h-none">
        <table className="w-full min-w-[1080px] border-collapse text-xs">
          <thead className="sticky top-0 z-10 bg-slate-50 text-slate-600 shadow-[0_1px_0_0_#e2e8f0]">
            <tr>
              {sortHeader("season", labels.col.season)}
              {sortHeader("phase", labels.col.phase)}
              {sortHeader("parameter", labels.col.parameter)}
              {sortHeader("value", labels.col.value)}
              {plainHeader(labels.col.unit)}
              {plainHeader(labels.col.state)}
              {plainHeader(labels.col.criterion)}
              {plainHeader(labels.col.siteAsPrinted)}
              {plainHeader(labels.col.source)}
              {plainHeader(labels.col.csvLine)}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr>
                <td colSpan={10} className="px-3 py-8 text-center text-slate-500">
                  {labels.empty}
                </td>
              </tr>
            )}
            {visible.map((r) => {
              const missing = !READING_STATES.has(r.state);
              return (
                <tr key={r.key} className={`border-b border-slate-100 align-top last:border-0 ${missing ? "bg-slate-50/70" : "hover:bg-slate-50"}`}>
                  <td className="px-2 py-1.5 whitespace-nowrap">{r.seasonText}</td>
                  <td className="px-2 py-1.5 whitespace-nowrap">{r.phaseText}</td>
                  <td className="px-2 py-1.5">
                    <span className="font-medium text-slate-900">{r.paramText}</span>
                    {r.parameterAsPrinted && r.parameterAsPrinted !== r.parameter && (
                      <span className="block text-[11px] text-slate-500">
                        {labels.col.printedAs}: “{r.parameterAsPrinted}”
                      </span>
                    )}
                  </td>
                  <td className="px-2 py-1.5">
                    <CellValue state={r.state} printed={r.valueAsPrinted ?? undefined} short={r.short} title={r.cellTitle} />
                  </td>
                  <td className="px-2 py-1.5 whitespace-nowrap text-slate-600">{r.unit || "—"}</td>
                  <td className="px-2 py-1.5 text-slate-700">
                    {r.stateText}
                    {r.rawFlag && r.rawFlag !== r.valueAsPrinted && (
                      <span className="block text-[11px] text-slate-500">
                        {labels.flagLabel}: “{r.rawFlag}”
                      </span>
                    )}
                  </td>
                  <td className="px-2 py-1.5 text-slate-600">{r.criterion}</td>
                  <td className="max-w-[16rem] px-2 py-1.5 text-slate-600">
                    {r.siteAsPrinted ?? <span className="text-slate-400 italic">{labels.noRow}</span>}
                  </td>
                  <td className="px-2 py-1.5">
                    {r.source && r.sourceText && r.sourceStatus ? (
                      <SourceRefLink source={r.source} text={r.sourceText} statusText={r.sourceStatus} stacked />
                    ) : (
                      <span className="text-slate-400">{labels.noPage}</span>
                    )}
                  </td>
                  <td className="px-2 py-1.5 text-slate-500 tabular-nums">{r.csvLine ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
