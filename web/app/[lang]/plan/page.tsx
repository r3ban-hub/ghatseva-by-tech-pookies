import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPlanWindows, getRanking, getRecommendedActions, getTaskGroups } from "@/lib/data";
import { getDictionary, isLang, pick } from "@/lib/i18n";
import { ghatHref } from "@/lib/screens";
import { Section } from "@/components/ui/Section";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { PlanBoard, type PlanRowView } from "@/components/plan/PlanBoard";

export async function generateMetadata({ params }: PageProps<"/[lang]/plan">): Promise<Metadata> {
  const { lang } = await params;
  return isLang(lang) ? { title: getDictionary(lang).plan.title } : {};
}

const day = (iso: string) => Number(iso.slice(8, 10));

export default async function PlanPage({ params }: PageProps<"/[lang]/plan">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const t = getDictionary(lang);
  const p = t.plan;
  const [sites, windows, groups] = await Promise.all([getRanking(), getPlanWindows(), getTaskGroups()]);
  const groupInfo = new Map(groups.map((g) => [g.group, g]));

  const rows: PlanRowView[] = [];
  for (const site of sites) {
    for (const action of await getRecommendedActions(site.siteId)) {
      const info = groupInfo.get(action.taskGroup);
      rows.push({
        key: `${site.siteId}-${action.id}`,
        siteId: site.siteId,
        siteName: pick(site.name, lang),
        rank: site.rank,
        href: ghatHref(lang, site.siteId),
        group: action.taskGroup,
        groupText: t.ghat.actions.groups[action.taskGroup],
        task: pick(action.text, lang),
        dates: pick(action.dates, lang),
        window: action.window,
        startDay: day(action.start),
        endDay: day(action.end),
        roleExample: info ? pick(info.roleExample, lang) : "",
        outcome: info ? pick(info.outcome, lang) : "",
      });
    }
  }
  rows.sort((a, b) => a.startDay - b.startDay || a.rank - b.rank);

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{p.title}</h1>
        <p className="max-w-3xl text-sm text-slate-600">{p.intro}</p>
      </header>

      <Section
        title={p.windows}
        aside={<ProvenanceTag provenance="prd" label={t.provenance.prd} detail="§7.3" title={t.provenance.prdLong} />}
      >
        <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          {windows.map((w) => (
            <li
              key={w.id}
              className={`rounded border px-3 py-2 text-xs ${w.id === "w4" ? "border-navy bg-navy-soft" : "border-slate-200"}`}
            >
              <p className="font-semibold text-slate-900">
                {pick(w.dates, lang)} <span className="font-normal text-slate-400">({w.label})</span>
              </p>
              <p className="mt-0.5 text-slate-700">{pick(w.activities, lang)}</p>
            </li>
          ))}
        </ol>
        <p className="mt-3 border-l-4 border-navy bg-navy-soft/60 px-3 py-2 text-xs text-slate-800">{p.target}</p>
      </Section>

      <Section
        title={p.timeline}
        subtitle={p.roleNote}
        aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="plan.py" title={t.provenance.backendLong} />}
      >
        <PlanBoard
          rows={rows}
          ghats={sites.map((s) => ({ value: s.siteId, text: `#${s.rank} ${pick(s.name, lang)}` }))}
          groups={groups.map((g) => ({ value: g.group, text: t.ghat.actions.groups[g.group] }))}
          labels={{
            allGhats: t.common.allGhats,
            allGroups: t.common.allGroups,
            ghat: t.common.ghat,
            taskGroup: t.common.taskGroup,
            assignBlank: t.common.assignBlank,
            recommendation: t.common.recommendation,
            immersion: p.immersion,
            showing: p.showing,
            empty: p.empty,
            col: p.col,
          }}
        />
      </Section>
    </div>
  );
}
