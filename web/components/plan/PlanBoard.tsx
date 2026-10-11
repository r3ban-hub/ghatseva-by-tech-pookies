"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

export interface PlanRowView {
  key: string;
  siteId: string;
  siteName: string;
  rank: number;
  href: string;
  group: string;
  groupText: string;
  task: string;
  dates: string;
  window: string;
  startDay: number;
  endDay: number;
  /** Assigned role from the backend (e.g. the assumed sampling role), or null when unassigned. */
  role: string | null;
  roleExample: string;
  outcome: string;
}

export interface PlanLabels {
  allGhats: string;
  allGroups: string;
  ghat: string;
  taskGroup: string;
  assignBlank: string;
  recommendation: string;
  immersion: string;
  showing: string;
  empty: string;
  col: { ghat: string; task: string; when: string; role: string; outcome: string; status: string };
}

const DAYS = Array.from({ length: 17 }, (_, i) => 11 + i); // 11–27 Oct
const IMMERSION = 20;
// Narrower label column and a minimum day width on phones; the label column wraps to two lines.
const ROW_GRID = "grid grid-cols-[10rem_repeat(17,minmax(1.6rem,1fr))] sm:grid-cols-[16rem_repeat(17,minmax(0,1fr))]";

/** Filterable timeline + task table. Rows (tasks, dates, roles) are supplied; the board only filters them. */
export function PlanBoard({
  rows,
  ghats,
  groups,
  labels,
}: {
  rows: PlanRowView[];
  ghats: { value: string; text: string }[];
  groups: { value: string; text: string }[];
  labels: PlanLabels;
}) {
  const [ghat, setGhat] = useState("all");
  const [group, setGroup] = useState("all");
  const visible = useMemo(
    () => rows.filter((r) => (ghat === "all" || r.siteId === ghat) && (group === "all" || r.group === group)),
    [rows, ghat, group],
  );

  const select = (label: string, value: string, onChange: (v: string) => void, options: { value: string; text: string }[], all: string) => (
    <label className="flex flex-col gap-0.5 text-[11px] font-medium text-slate-600">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)} className="rounded border border-slate-300 bg-white px-2 py-1 text-xs text-slate-800">
        <option value="all">{all}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.text}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <div className="flex flex-col gap-4">
      <div className="no-print flex flex-wrap items-end gap-3">
        {select(labels.ghat, ghat, setGhat, ghats, labels.allGhats)}
        {select(labels.taskGroup, group, setGroup, groups, labels.allGroups)}
        <p className="ml-auto text-xs text-slate-500" aria-live="polite">
          {labels.showing.replace("{n}", String(visible.length)).replace("{N}", String(rows.length))}
        </p>
      </div>

      {/* Timeline */}
      <div className="overflow-x-auto rounded border border-slate-200 print:overflow-visible [print-color-adjust:exact]">
        <div className="min-w-[38rem] sm:min-w-[900px] print:min-w-0">
          <div className={`${ROW_GRID} border-b border-slate-200 bg-slate-50 text-[10.5px] text-slate-600`}>
            <div className="px-2 py-1.5 font-medium">{labels.col.task}</div>
            {DAYS.map((d) => (
              <div
                key={d}
                className={`py-1.5 text-center tabular-nums ${d === IMMERSION ? "bg-navy font-semibold text-white" : ""}`}
                title={d === IMMERSION ? labels.immersion : undefined}
              >
                {d}
              </div>
            ))}
          </div>
          {visible.map((r) => (
            <div key={r.key} className={`${ROW_GRID} border-b border-slate-100 text-xs last:border-0`}>
              <div className="min-w-0 px-2 py-1 leading-tight" title={`${r.siteName} · ${r.groupText}`}>
                <div className="truncate">
                  <span className="font-semibold text-slate-500 tabular-nums">#{r.rank}</span>{" "}
                  <span className="text-slate-900">{r.siteName}</span>
                </div>
                <div className="truncate text-slate-500">{r.groupText}</div>
              </div>
              {DAYS.map((d) => {
                const active = d >= r.startDay && d <= r.endDay;
                return (
                  <div key={d} className={`flex items-center ${d === IMMERSION ? "bg-navy-soft" : ""}`}>
                    {active && (
                      <div
                        title={`${r.task} (${r.dates})`}
                        className={`h-4 w-full ${d === r.startDay ? "ml-0.5 rounded-l-sm" : ""} ${d === r.endDay ? "mr-0.5 rounded-r-sm" : ""} border-y border-accent bg-accent/80`}
                      />
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
        {visible.length === 0 && <p className="px-3 py-6 text-center text-sm text-slate-500">{labels.empty}</p>}
      </div>

      {/* Task table */}
      {visible.length > 0 && (
      <div className="overflow-x-auto rounded border border-slate-200 print:overflow-visible">
        <table className="w-full min-w-[980px] border-collapse text-xs print:min-w-0">
          <thead className="bg-slate-50 text-left text-slate-600">
            <tr className="border-b border-slate-200">
              {[labels.col.ghat, labels.col.task, labels.col.when, labels.col.role, labels.col.outcome, labels.col.status].map((h) => (
                <th key={h} scope="col" className="px-2 py-2 font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((r) => (
              <tr key={r.key} className="border-b border-slate-100 align-top last:border-0">
                <td className="min-w-[9rem] px-2 py-2">
                  <span className="font-semibold text-slate-500 tabular-nums">#{r.rank}</span>{" "}
                  <Link href={r.href} className="font-medium text-slate-900 hover:text-navy hover:underline">
                    {r.siteName}
                  </Link>
                </td>
                <td className="px-2 py-2">
                  <span className="font-medium text-slate-900">{r.groupText}</span>
                  <p className="text-slate-700">{r.task}</p>
                </td>
                <td className="px-2 py-2 whitespace-nowrap">
                  <span className="font-medium text-slate-900">{r.dates}</span>
                  <span className="block text-[11px] text-slate-500">{r.window}</span>
                </td>
                <td className="px-2 py-2">
                  {r.role ? (
                    <span className="font-medium text-slate-900">{r.role}</span>
                  ) : (
                    <>
                      <span className="font-medium text-slate-900">{labels.assignBlank}</span>
                      <span className="block text-[11px] text-slate-500">{r.roleExample}</span>
                    </>
                  )}
                </td>
                <td className="px-2 py-2 text-slate-700">{r.outcome}</td>
                <td className="px-2 py-2">
                  <span className="inline-block min-w-[9rem] rounded-sm border border-dashed border-slate-400 px-1.5 py-px text-[11px] text-slate-700">
                    {labels.recommendation}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      )}
    </div>
  );
}
