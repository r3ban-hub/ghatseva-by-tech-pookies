import { Square } from "lucide-react";
import type { Lang, PrintedName, RecommendedAction, SiteRanking, TargetStandard, TaskGroupInfo, WorkOrderMeta } from "@/lib/data/types";
import { fill, pick, type Dictionary } from "@/lib/i18n";
import { FLAG_ORDER, FLAG_SEVERITY } from "@/lib/flags";
import { TierBadge } from "@/components/data/TierBadge";
import { FlagChip } from "@/components/data/FlagChip";

interface Props {
  site: SiteRanking;
  actions: RecommendedAction[];
  groups: TaskGroupInfo[];
  meta: WorkOrderMeta;
  standard: TargetStandard;
  printedNames: PrintedName[];
  reasons: string[];
  lang: Lang;
  t: Dictionary;
}

/** A4 draft work order. Roles and zone stay blank ("Assign: ____"); no costs, names or contacts. */
export function WorkOrder({ site, actions, groups, meta, standard, printedNames, reasons, lang, t }: Props) {
  const o = t.orders;
  const where = printedNames.at(-1)?.name ?? site.csvSiteName;
  const sorted = [...actions].sort((a, b) => a.start.localeCompare(b.start));
  const groupInfo = new Map(groups.map((g) => [g.group, g]));

  return (
    <article className="mx-auto w-full max-w-[210mm] rounded-md border border-slate-300 bg-white px-6 py-5 text-sm shadow-sm print:max-w-none print:border-0 print:p-0 print:shadow-none">
      <p className="hatch rounded border border-dashed border-slate-500 bg-white px-3 py-1.5 text-xs font-semibold text-slate-900">{o.draft}</p>

      <header className="mt-3 flex flex-wrap items-start justify-between gap-3 border-b border-slate-300 pb-3">
        <div>
          <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">{o.orderTitle}</p>
          <h1 className="text-xl font-semibold text-slate-900">{pick(site.name, lang)}</h1>
          {lang === "hi" && <p className="text-xs text-slate-500">{site.name.en}</p>}
          <p className="text-xs text-slate-700">{pick(site.waterBody, lang)}</p>
        </div>
        <div className="flex flex-col items-end gap-1 text-xs">
          <div className="flex items-center gap-2">
            <TierBadge tier={site.tier} label={fill(t.tier.label, { n: site.tier })} />
            {site.highRisk && <span className="font-semibold tracking-wide text-risk-red uppercase">{t.overview.ranking.highRisk}</span>}
          </div>
          <p>
            <span className="text-slate-500">{o.zone}:</span> <span className="font-medium">{t.common.assignBlank}</span>
          </p>
          <p>
            <span className="text-slate-500">{o.issuedBy}:</span> {pick(meta.issuedByRole, lang)}
          </p>
          <p>
            <span className="text-slate-500">{o.date}:</span> {o.dateValue}
          </p>
        </div>
      </header>

      <section className="mt-3">
        <h2 className="text-sm font-semibold text-slate-900">{o.why}</h2>
        <div className="mt-1 flex flex-wrap gap-1">
          {FLAG_ORDER.filter((f) => site.flags.includes(f)).map((f) => (
            <FlagChip key={f} severity={FLAG_SEVERITY[f]} label={t.flag[f].short} identity={f === "SITE_IDENTITY"} />
          ))}
        </div>
        <ul className="mt-1.5 list-disc space-y-0.5 pl-5 text-xs text-slate-800">
          {reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      </section>

      <section className="mt-3">
        <h2 className="text-sm font-semibold text-slate-900">{o.tasks}</h2>
        <table className="mt-1 w-full border-collapse text-xs">
          <thead className="text-left text-slate-600">
            <tr className="border-b border-slate-300">
              <th scope="col" className="w-6 py-1">#</th>
              <th scope="col" className="py-1 pr-2">{o.col.what}</th>
              <th scope="col" className="py-1 pr-2">{o.col.when}</th>
              <th scope="col" className="py-1 pr-2">{o.col.role}</th>
              <th scope="col" className="py-1 pr-2 text-center">{o.col.done}</th>
              <th scope="col" className="w-24 py-1">{o.col.remarks}</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((a, i) => (
              <tr key={a.id} className="print-break-avoid border-b border-slate-200 align-top">
                <td className="py-1.5 text-slate-500 tabular-nums">{i + 1}</td>
                <td className="py-1.5 pr-2">
                  <span className="font-medium text-slate-900">{t.ghat.actions.groups[a.taskGroup]}</span>
                  <p className="text-slate-800">{pick(a.text, lang)}</p>
                  <p className="text-[11px] text-slate-500 italic">{t.common.recommendation}</p>
                </td>
                <td className="py-1.5 pr-2 font-medium whitespace-nowrap">{pick(a.dates, lang)}</td>
                <td className="py-1.5 pr-2">
                  <span className="font-medium">{t.common.assignBlank}</span>
                  <span className="block text-[11px] text-slate-500">{pick(groupInfo.get(a.taskGroup)?.roleExample ?? { en: "", hi: "" }, lang)}</span>
                </td>
                <td className="py-1.5 pr-2 text-center">
                  <Square aria-label={o.col.done} className="inline h-4 w-4 text-slate-500" />
                </td>
                <td className="py-1.5 text-slate-300">__________</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-1.5 text-xs text-slate-700">
          <span className="text-slate-500">{o.col.where}:</span> “{where}” · {o.locationNote}
        </p>
      </section>

      <section className="mt-3">
        <h2 className="text-sm font-semibold text-slate-900">{o.target}</h2>
        <ul className="mt-1 grid gap-1 text-xs sm:grid-cols-2">
          {standard.items.map((item) => (
            <li key={item.id} className="flex items-center gap-1.5">
              <Square aria-hidden className="h-3.5 w-3.5 text-slate-500" />
              <span className="font-medium">{pick(item.parameter, lang)}</span> {pick(item.target, lang)}
              {!item.inCurrentData && <span className="text-[11px] text-slate-500">({t.ghat.target.notInData})</span>}
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-3">
        <h2 className="text-sm font-semibold text-slate-900">{fill(o.reportBack, { date: pick(meta.reportBackBy, lang) })}</h2>
        <ul className="mt-1 grid gap-1 text-xs sm:grid-cols-2">
          {meta.reportBackItems.map((item) => (
            <li key={item.en} className="flex items-center gap-1.5">
              <Square aria-hidden className="h-3.5 w-3.5 text-slate-500" />
              {pick(item, lang)}
            </li>
          ))}
        </ul>
        <p className="mt-1 text-[11px] text-slate-500">{o.noCost}</p>
      </section>

      <footer className="mt-4 border-t border-slate-300 pt-2 text-[11px] text-slate-600">{o.footer}</footer>
    </article>
  );
}
