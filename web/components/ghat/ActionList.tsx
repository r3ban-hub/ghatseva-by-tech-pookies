import { CalendarDays } from "lucide-react";
import type { FlagCode, Lang, RecommendedAction } from "@/lib/data/types";
import { pick, type Dictionary } from "@/lib/i18n";
import { FLAG_SEVERITY } from "@/lib/flags";
import { Section } from "@/components/ui/Section";
import { FlagChip } from "@/components/data/FlagChip";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";

/** PRD v2 §7.2 actions for this ghat. All are recommendations pending verification. */
export function ActionList({ actions, lang, t }: { actions: RecommendedAction[]; lang: Lang; t: Dictionary }) {
  const a = t.ghat.actions;
  return (
    <Section
      id="actions"
      title={a.title}
      subtitle={a.subtitle}
      aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="action_rules.csv" title={t.provenance.backendLong} />}
    >
      <ol className="divide-y divide-slate-100">
        {actions.map((action) => (
          <li key={action.id} className="py-2.5 first:pt-0 last:pb-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs">
              <span className="font-semibold text-slate-900">{a.groups[action.taskGroup]}</span>
              <span className="text-slate-300">·</span>
              <span className="text-slate-500">{a.because}:</span>
              {action.trigger === "ALL" ? (
                <span className="text-slate-700">{a.allGhats}</span>
              ) : (
                ((action.triggers ?? [action.trigger]).filter((f): f is FlagCode => f in FLAG_SEVERITY)).map((f) => (
                  <FlagChip key={f} severity={FLAG_SEVERITY[f]} label={t.flag[f].short} title={t.flag[f].long} identity={f === "SITE_IDENTITY"} />
                ))
              )}
            </div>
            <p className="mt-1 text-sm text-slate-800">{pick(action.text, lang)}</p>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
              <span className="inline-flex items-center gap-1 font-medium text-slate-800">
                <CalendarDays aria-hidden className="h-3.5 w-3.5 text-slate-400" />
                {a.when}: {pick(action.dates, lang)}
                <span className="font-normal text-slate-400">({action.window})</span>
              </span>
              {!action.verified && (
                <span className="rounded-sm border border-dashed border-slate-400 px-1.5 py-px text-[11px] text-slate-700">{a.verify}</span>
              )}
              <span className="text-[11px] text-slate-500 italic">{pick(action.sourceStatus, lang)}</span>
            </div>
          </li>
        ))}
      </ol>
    </Section>
  );
}
