import { CalendarClock, Square } from "lucide-react";
import type { Lang, TargetStandard } from "@/lib/data/types";
import { pick, type Dictionary } from "@/lib/i18n";
import { Section } from "@/components/ui/Section";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";

/** The 27 Oct target from PRD v2 §7.1. Unchecked boxes: there are no 2026 readings. */
export function TargetChecklist({ standard, lang, t }: { standard: TargetStandard; lang: Lang; t: Dictionary }) {
  const g = t.ghat.target;
  return (
    <Section
      id="target"
      title={g.title}
      subtitle={g.subtitle}
      aside={<ProvenanceTag provenance="prd" label={t.provenance.prd} detail="§7.1" title={t.provenance.prdLong} />}
    >
      <div className="flex flex-col gap-3">
        <p className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-900">
          <CalendarClock aria-hidden className="h-4 w-4 text-slate-500" />
          {g.sampleDue}
        </p>

        <div className="hatch rounded border border-slate-300 bg-missing-bg px-3 py-2 text-xs text-slate-800">
          <span className="font-semibold">{g.currentStatus}:</span> {pick(standard.currentStatus, lang)}
        </div>

        <div>
          <h3 className="text-xs font-semibold tracking-wide text-slate-500 uppercase">{g.checklist}</h3>
          <ul className="mt-1.5 divide-y divide-slate-100 rounded border border-slate-200">
            {standard.items.map((item) => (
              <li key={item.id} className="flex items-start gap-2 px-3 py-2 text-sm">
                <Square aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" />
                <div className="min-w-0">
                  <span className="font-medium text-slate-900">{pick(item.parameter, lang)}</span>{" "}
                  <span className="text-slate-700">{pick(item.target, lang)}</span>
                  {!item.inCurrentData && (
                    <span className="hatch ml-2 inline-block rounded-sm border border-dashed border-slate-400 bg-white px-1.5 text-[11px] text-slate-700">
                      {g.notInData}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-xs font-semibold tracking-wide text-slate-500 uppercase">{g.statuses}</h3>
          <dl className="mt-1.5 space-y-1.5 text-xs">
            {standard.statuses.map((s) => (
              <div key={s.id}>
                <dt className="font-medium text-slate-900">{pick(s.label, lang)}</dt>
                <dd className="text-slate-600">{pick(s.rule, lang)}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-2 border-l-4 border-navy bg-navy-soft/60 px-3 py-2 text-xs text-slate-800">{pick(standard.interimNote, lang)}</p>
        </div>
      </div>
    </Section>
  );
}
