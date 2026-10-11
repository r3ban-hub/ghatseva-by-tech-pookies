import type { CellState, SiteEvidence } from "@/lib/data/types";
import type { Dictionary } from "@/lib/i18n";
import { countStates } from "@/lib/evidence-view";
import { paramName, seasonLabel } from "@/lib/format";
import { Section } from "@/components/ui/Section";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { CellValue } from "./CellValue";
import { cellTitle } from "./ReadingMiniTable";

const LEGEND: CellState[] = ["numeric", "bdl", "nd", "not_sampled", "no_table", "unknown_flag", "invalid_value"];
const LEGEND_SAMPLE: Partial<Record<CellState, string>> = { numeric: "6.4", bdl: "BDL", nd: "ND" };

/** Seasons × phases across, parameters down. Every expected cell is shown in its state; none is coloured by limits. */
export function CoverageGrid({ evidence, t }: { evidence: SiteEvidence; t: Dictionary }) {
  const c = t.ghat.coverage;
  const counts = countStates(evidence.cells);
  const cellAt = new Map(evidence.cells.map((cell) => [`${cell.year}|${cell.festival}|${cell.phase}|${cell.parameter}`, cell]));

  return (
    <Section
      id="coverage"
      title={c.title}
      subtitle={c.subtitle}
      aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="evidence.py" title={t.provenance.backendLong} />}
    >
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-700">
        <span className="font-medium text-slate-500">{c.legend}:</span>
        {LEGEND.map((state) => (
          <span key={state} className="inline-flex items-center gap-1.5">
            <CellValue state={state} printed={LEGEND_SAMPLE[state]} short={t.valueStateShort[state] || "6.4"} title={t.valueState[state]} compact />
            <span>
              {t.valueState[state]} <span className="text-slate-500 tabular-nums">({counts[state]})</span>
            </span>
          </span>
        ))}
      </div>

      <div className="overflow-x-auto rounded border border-slate-200">
        <table className="w-full min-w-[980px] border-collapse text-xs">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th scope="col" rowSpan={2} className="sticky left-0 z-10 border-r border-b border-slate-200 bg-slate-50 px-2 py-1.5 text-left font-medium">
                {c.parameter}
              </th>
              {evidence.seasons.map((s) => (
                <th key={`${s.year}-${s.festival}`} scope="colgroup" colSpan={3} className="border-b border-l border-slate-200 px-1 py-1 text-center font-semibold text-slate-800">
                  {seasonLabel(s, t)}
                </th>
              ))}
            </tr>
            <tr>
              {evidence.seasons.flatMap((s) =>
                evidence.phases.map((p, i) => (
                  <th
                    key={`${s.year}-${s.festival}-${p}`}
                    scope="col"
                    title={t.phase[p]}
                    className={`border-b border-slate-200 px-1 py-1 text-center text-[10.5px] font-medium ${i === 0 ? "border-l" : ""}`}
                  >
                    {t.phaseShort[p]}
                  </th>
                )),
              )}
            </tr>
          </thead>
          <tbody>
            {evidence.parameters.map((param) => (
              <tr key={param} className="border-b border-slate-100 last:border-0">
                <th scope="row" className="sticky left-0 z-10 border-r border-slate-200 bg-white px-2 py-1 text-left font-medium whitespace-nowrap text-slate-800">
                  {paramName(param, t)}
                </th>
                {evidence.seasons.flatMap((s) =>
                  evidence.phases.map((p, i) => {
                    const cell = cellAt.get(`${s.year}|${s.festival}|${p}|${param}`);
                    return (
                      <td key={`${s.year}-${s.festival}-${p}`} className={`px-0.5 py-0.5 text-center ${i === 0 ? "border-l border-slate-200" : ""}`}>
                        {cell && (
                          <CellValue
                            state={cell.state}
                            printed={cell.reading?.valueAsPrinted}
                            short={t.valueStateShort[cell.state]}
                            title={`${seasonLabel(s, t)} · ${t.phase[p]} · ${paramName(param, t)}: ${cellTitle(cell, t)}`}
                            compact
                          />
                        )}
                      </td>
                    );
                  }),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
