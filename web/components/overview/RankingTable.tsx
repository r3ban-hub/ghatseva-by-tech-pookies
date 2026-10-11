"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronRight } from "lucide-react";
import type { FlagSeverity, Fraction, Tier } from "@/lib/data/types";
import { TierBadge } from "@/components/data/TierBadge";
import { FlagChip } from "@/components/data/FlagChip";
import { FractionBar } from "@/components/data/FractionBar";
import { CoverageMeter, type CoverageItem } from "@/components/data/CoverageMeter";

/** One row, fully prepared on the server. The table only sorts and filters supplied values. */
export interface RankingRowView {
  siteId: string;
  href: string;
  rank: number;
  tier: Tier;
  tierLabel: string;
  tierTitle: string;
  highRisk: boolean;
  name: string;
  nameSecondary?: string;
  waterBody: string;
  identityMedium: boolean;
  doBelow5: Fraction;
  doBelow5Label: string;
  doBelow4: number;
  doMin: string;
  bodAbove3: Fraction;
  bodAbove3Label: string;
  phOut: Fraction;
  phOutLabel: string;
  coverage: CoverageItem[];
  flags: { code: string; severity: FlagSeverity; label: string; title: string }[];
  openLabel: string;
}

export interface RankingTableLabels {
  col: Record<
    "rank" | "ghat" | "tier" | "doBelow5" | "doBelow4" | "doMin" | "bodAbove3" | "phOut" | "coverage" | "flags",
    string
  >;
  unitMgL: string;
  sortBy: string;
  highRisk: string;
  identityMedium: string;
  filterAll: string;
  filterHigh: string;
  showing: string;
  empty: string;
}

type SortKey = "rank" | "name" | "tier" | "doBelow5" | "doBelow4" | "doMin" | "bodAbove3" | "phOut";
type Dir = "asc" | "desc";

const ratio = (f: Fraction) => (f.N > 0 ? f.n / f.N : -1);

// Display-order comparators over supplied values. Ties fall back to the official rank.
const VALUE: Record<SortKey, (r: RankingRowView) => number | string> = {
  rank: (r) => r.rank,
  name: (r) => r.name,
  tier: (r) => r.tier,
  doBelow5: (r) => ratio(r.doBelow5),
  doBelow4: (r) => r.doBelow4,
  doMin: (r) => Number(r.doMin),
  bodAbove3: (r) => ratio(r.bodAbove3),
  phOut: (r) => ratio(r.phOut),
};

// First click shows the most concerning end first.
const FIRST_DIR: Record<SortKey, Dir> = {
  rank: "asc",
  name: "asc",
  tier: "asc",
  doBelow5: "desc",
  doBelow4: "desc",
  doMin: "asc",
  bodAbove3: "desc",
  phOut: "desc",
};

function fillCount(template: string, n: number, N: number) {
  return template.replace("{n}", String(n)).replace("{N}", String(N));
}

export function RankingTable({ rows, labels }: { rows: RankingRowView[]; labels: RankingTableLabels }) {
  const [sort, setSort] = useState<{ key: SortKey; dir: Dir }>({ key: "rank", dir: "asc" });
  const [highOnly, setHighOnly] = useState(false);

  const visible = useMemo(() => {
    const filtered = highOnly ? rows.filter((r) => r.highRisk) : rows;
    const get = VALUE[sort.key];
    return [...filtered].sort((a, b) => {
      const va = get(a);
      const vb = get(b);
      const cmp = typeof va === "string" ? va.localeCompare(vb as string) : (va as number) - (vb as number);
      if (cmp !== 0) return sort.dir === "asc" ? cmp : -cmp;
      return a.rank - b.rank;
    });
  }, [rows, sort, highOnly]);

  const toggle = (key: SortKey) =>
    setSort((s) => (s.key === key ? { key, dir: s.dir === "asc" ? "desc" : "asc" } : { key, dir: FIRST_DIR[key] }));

  const header = (key: SortKey, text: string, align: "left" | "right" = "left") => {
    const active = sort.key === key;
    const Icon = !active ? ArrowUpDown : sort.dir === "asc" ? ArrowUp : ArrowDown;
    return (
      <th
        scope="col"
        aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : "none"}
        className={`px-2 py-2 font-medium whitespace-nowrap ${align === "right" ? "text-right" : "text-left"}`}
      >
        <button
          type="button"
          onClick={() => toggle(key)}
          title={labels.sortBy.replace("{col}", text)}
          className={`inline-flex items-center gap-1 rounded px-1 py-0.5 transition-colors hover:bg-slate-200/70 hover:text-slate-900 ${
            active ? "text-slate-900" : ""
          }`}
        >
          {text}
          <Icon aria-hidden className={`h-3 w-3 ${active ? "text-navy" : "text-slate-400"}`} />
        </button>
      </th>
    );
  };

  return (
    <div>
      <div className="no-print mb-3 flex flex-wrap items-center justify-between gap-2">
        <div role="group" className="inline-flex rounded border border-slate-300 p-0.5 text-xs">
          {[
            { value: false, text: labels.filterAll },
            { value: true, text: labels.filterHigh },
          ].map((opt) => (
            <button
              key={String(opt.value)}
              type="button"
              aria-pressed={highOnly === opt.value}
              onClick={() => setHighOnly(opt.value)}
              className={
                highOnly === opt.value
                  ? "rounded-sm bg-navy px-2.5 py-1 font-medium text-white"
                  : "rounded-sm px-2.5 py-1 text-slate-700 transition-colors hover:bg-slate-100"
              }
            >
              {opt.text}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500" aria-live="polite">
          {fillCount(labels.showing, visible.length, rows.length)}
        </p>
      </div>

      <div className="overflow-x-auto rounded border border-slate-200">
        <table className="w-full min-w-[960px] border-collapse text-sm">
          <thead className="bg-slate-50 text-xs text-slate-600">
            <tr className="border-b border-slate-200">
              {header("rank", labels.col.rank, "right")}
              {header("name", labels.col.ghat)}
              {header("tier", labels.col.tier)}
              {header("doBelow5", labels.col.doBelow5, "right")}
              {header("doBelow4", labels.col.doBelow4, "right")}
              {header("doMin", `${labels.col.doMin} (${labels.unitMgL})`, "right")}
              {header("bodAbove3", labels.col.bodAbove3, "right")}
              {header("phOut", labels.col.phOut, "right")}
              <th scope="col" className="px-2 py-2 text-left font-medium whitespace-nowrap">
                {labels.col.coverage}
              </th>
              <th scope="col" className="px-2 py-2 text-left font-medium whitespace-nowrap">
                {labels.col.flags}
              </th>
              <th scope="col" className="w-8 px-2 py-2">
                <span className="sr-only">{labels.col.ghat}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 && (
              <tr>
                <td colSpan={11} className="px-3 py-8 text-center text-sm text-slate-500">
                  {labels.empty}
                </td>
              </tr>
            )}
            {visible.map((r) => (
              <tr key={r.siteId} className="border-b border-slate-100 align-top transition-colors last:border-0 hover:bg-slate-50">
                <td className="px-2 py-2.5 text-right text-base font-semibold text-slate-900 tabular-nums">{r.rank}</td>
                <td className="px-2 py-2.5">
                  <Link href={r.href} className="font-medium text-slate-900 underline-offset-2 hover:text-navy hover:underline">
                    {r.name}
                  </Link>
                  {r.nameSecondary && <div className="text-[11px] text-slate-500">{r.nameSecondary}</div>}
                  <div className="text-xs text-slate-500">{r.waterBody}</div>
                  {r.identityMedium && (
                    <div className="mt-1">
                      <FlagChip severity="neutral" identity label={labels.identityMedium} />
                    </div>
                  )}
                </td>
                <td className="px-2 py-2.5">
                  <div className="flex flex-col items-start gap-1">
                    <TierBadge tier={r.tier} label={r.tierLabel} title={r.tierTitle} />
                    {r.highRisk && (
                      <span className="text-[11px] font-semibold tracking-wide whitespace-nowrap text-risk-red uppercase">
                        {labels.highRisk}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-2 py-2.5 text-right">
                  <FractionBar value={r.doBelow5} text={`${r.doBelow5.n}/${r.doBelow5.N}`} label={r.doBelow5Label} />
                </td>
                <td className="px-2 py-2.5 text-right font-medium tabular-nums">
                  <span className={r.doBelow4 > 0 ? "text-risk-red" : "text-slate-500"}>{r.doBelow4}</span>
                </td>
                <td className="px-2 py-2.5 text-right font-medium tabular-nums">{r.doMin}</td>
                <td className="px-2 py-2.5 text-right">
                  <FractionBar value={r.bodAbove3} text={`${r.bodAbove3.n}/${r.bodAbove3.N}`} label={r.bodAbove3Label} width="w-12" />
                </td>
                <td className="px-2 py-2.5 text-right">
                  <FractionBar value={r.phOut} text={`${r.phOut.n}/${r.phOut.N}`} label={r.phOutLabel} width="w-12" />
                </td>
                <td className="px-2 py-2.5">
                  <CoverageMeter items={r.coverage} />
                </td>
                <td className="px-2 py-2.5">
                  <div className="flex max-w-[15rem] flex-wrap gap-1">
                    {r.flags.map((f) => (
                      <FlagChip key={f.code} severity={f.severity} label={f.label} title={f.title} identity={f.code === "SITE_IDENTITY"} />
                    ))}
                  </div>
                </td>
                <td className="px-2 py-2.5 text-right">
                  <Link
                    href={r.href}
                    aria-label={r.openLabel}
                    className="inline-flex h-7 w-7 items-center justify-center rounded text-slate-400 transition-colors hover:bg-navy-soft hover:text-navy"
                  >
                    <ChevronRight aria-hidden className="h-4 w-4" />
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
