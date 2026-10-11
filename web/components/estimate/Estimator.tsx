"use client";

import { useMemo, useState } from "react";
import { Eraser, FlaskConical } from "lucide-react";

export interface EstimatorLineView {
  id: string;
  item: string;
  unit: string;
}

export interface EstimatorLabels {
  loadIllustrative: string;
  clear: string;
  illustrativeBanner: string;
  enteredBanner: string;
  col: { item: string; unit: string; quantity: string; low: string; high: string; subtotal: string };
  rateNotSet: string;
  qtyNotSet: string;
  total: string;
  unset: string;
  allSet: string;
  partial: string;
  mockTag: string;
}

type Entry = { quantity: string; low: string; high: string };
const EMPTY: Entry = { quantity: "", low: "", high: "" };

const num = (s: string): number | null => {
  if (s.trim() === "") return null;
  const v = Number(s);
  return Number.isFinite(v) && v >= 0 ? v : null;
};
const inr = (v: number) => v.toLocaleString("en-IN", { maximumFractionDigits: 0 });

/**
 * quantity × rate calculator (PRD v2 §8). Uses only values typed on this page or the
 * explicitly loaded illustrative set. Nothing here feeds the brief or work orders.
 */
export function Estimator({
  lines,
  illustrative,
  labels,
}: {
  lines: EstimatorLineView[];
  illustrative: Record<string, { quantity: number; low: number; high: number }>;
  labels: EstimatorLabels;
}) {
  const [entries, setEntries] = useState<Record<string, Entry>>(() => Object.fromEntries(lines.map((l) => [l.id, EMPTY])));
  const [isIllustrative, setIsIllustrative] = useState(false);

  const update = (id: string, field: keyof Entry, value: string) => {
    setEntries((prev) => ({ ...prev, [id]: { ...prev[id], [field]: value } }));
  };

  const computed = useMemo(() => {
    let low = 0;
    let high = 0;
    let unset = 0;
    const rows = lines.map((l) => {
      const e = entries[l.id];
      const q = num(e.quantity);
      const lo = num(e.low);
      const hi = num(e.high) ?? lo; // a single rate gives a point estimate
      const complete = q !== null && lo !== null && hi !== null;
      if (complete) {
        low += q * Math.min(lo, hi);
        high += q * Math.max(lo, hi);
      } else unset += 1;
      return { ...l, e, q, lo, complete, subLow: complete ? q * Math.min(lo, hi) : null, subHigh: complete ? q * Math.max(lo, hi) : null };
    });
    return { rows, low, high, unset };
  }, [lines, entries]);

  const input = (id: string, field: keyof Entry, value: string, label: string, placeholder: string) => (
    <input
      type="number"
      inputMode="decimal"
      min={0}
      value={value}
      aria-label={label}
      placeholder={placeholder}
      onChange={(ev) => update(id, field, ev.target.value)}
      className={`w-24 rounded border px-2 py-1 text-right text-xs tabular-nums ${
        value === "" ? "hatch border-dashed border-slate-400 bg-white" : isIllustrative ? "border-slate-500 bg-white" : "border-slate-300 bg-white"
      }`}
    />
  );

  return (
    <div className="flex flex-col gap-3">
      <div className="no-print flex flex-wrap gap-2">
        {/* Shown only if a data source supplies illustrative values; the backend source supplies none. */}
        {Object.keys(illustrative).length > 0 && (
        <button
          type="button"
          onClick={() => {
            setEntries(
              Object.fromEntries(
                lines.map((l) => {
                  const v = illustrative[l.id];
                  return [l.id, v ? { quantity: String(v.quantity), low: String(v.low), high: String(v.high) } : EMPTY];
                }),
              ),
            );
            setIsIllustrative(true);
          }}
          className="inline-flex items-center gap-1.5 rounded border border-dashed border-slate-500 bg-white px-2.5 py-1 text-sm text-slate-800 hover:border-navy hover:text-navy"
        >
          <FlaskConical aria-hidden className="h-4 w-4" />
          {labels.loadIllustrative}
        </button>
        )}
        <button
          type="button"
          onClick={() => {
            setEntries(Object.fromEntries(lines.map((l) => [l.id, EMPTY])));
            setIsIllustrative(false);
          }}
          className="inline-flex items-center gap-1.5 rounded border border-slate-300 bg-white px-2.5 py-1 text-sm text-slate-800 hover:border-navy hover:text-navy"
        >
          <Eraser aria-hidden className="h-4 w-4" />
          {labels.clear}
        </button>
      </div>

      <p
        role="status"
        className={`rounded border px-3 py-2 text-xs ${
          isIllustrative ? "hatch border-dashed border-slate-600 bg-white font-semibold text-slate-900" : "border-slate-200 bg-slate-50 text-slate-700"
        }`}
      >
        {isIllustrative ? labels.illustrativeBanner : labels.enteredBanner}
      </p>

      <div className="overflow-x-auto rounded border border-slate-200">
        <table className="w-full min-w-[820px] border-collapse text-xs">
          <thead className="bg-slate-50 text-left text-slate-600">
            <tr className="border-b border-slate-200">
              <th scope="col" className="px-2 py-2 font-medium">{labels.col.item}</th>
              <th scope="col" className="px-2 py-2 font-medium">{labels.col.unit}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{labels.col.quantity}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{labels.col.low}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{labels.col.high}</th>
              <th scope="col" className="px-2 py-2 text-right font-medium">{labels.col.subtotal}</th>
            </tr>
          </thead>
          <tbody>
            {computed.rows.map((r) => (
              <tr key={r.id} className="border-b border-slate-100 last:border-0">
                <td className="px-2 py-1.5 font-medium text-slate-900">
                  {r.item}
                  {isIllustrative && <span className="hatch ml-2 rounded-sm border border-dashed border-slate-500 px-1 text-[10px] font-semibold">{labels.mockTag}</span>}
                </td>
                <td className="px-2 py-1.5 text-slate-600">{r.unit}</td>
                <td className="px-2 py-1.5 text-right">{input(r.id, "quantity", r.e.quantity, `${r.item}: ${labels.col.quantity}`, "—")}</td>
                <td className="px-2 py-1.5 text-right">{input(r.id, "low", r.e.low, `${r.item}: ${labels.col.low}`, labels.rateNotSet)}</td>
                <td className="px-2 py-1.5 text-right">{input(r.id, "high", r.e.high, `${r.item}: ${labels.col.high}`, labels.rateNotSet)}</td>
                <td className="px-2 py-1.5 text-right tabular-nums">
                  {r.complete && r.subLow !== null && r.subHigh !== null ? (
                    <span className="font-medium text-slate-900">
                      {r.subLow === r.subHigh ? inr(r.subLow) : `${inr(r.subLow)} – ${inr(r.subHigh)}`}
                    </span>
                  ) : (
                    <span className="text-slate-500 italic">{r.q === null ? labels.qtyNotSet : labels.rateNotSet}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-slate-300 bg-slate-50">
              <th scope="row" colSpan={5} className="px-2 py-2 text-left text-sm font-semibold text-slate-900">
                {labels.total}
                {computed.unset > 0 && <span className="ml-2 text-xs font-normal text-slate-600">({labels.partial})</span>}
              </th>
              <td className="px-2 py-2 text-right text-sm font-semibold text-slate-900 tabular-nums">
                {computed.unset === lines.length ? "—" : computed.low === computed.high ? `₹${inr(computed.low)}` : `₹${inr(computed.low)} – ₹${inr(computed.high)}`}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="text-xs font-medium text-slate-700" aria-live="polite">
        {computed.unset > 0 ? labels.unset.replace("{n}", String(computed.unset)).replace("{N}", String(lines.length)) : labels.allSet}
      </p>
    </div>
  );
}
