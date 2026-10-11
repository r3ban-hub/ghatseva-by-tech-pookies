import type { Metadata } from "next";
import { notFound } from "next/navigation";
import type { GridCell } from "@/lib/data/types";
import { getRanking, getRecommendedActions, getSite, getSiteEvidence, getTargetStandard } from "@/lib/data";
import { fill, getDictionary, isLang, pick, type Dictionary } from "@/lib/i18n";
import { countStates, isGap, isUsable, KEY_PARAMETERS } from "@/lib/evidence-view";
import { criterionText, paramName, refStatus, refText, seasonLabel } from "@/lib/format";
import { Section } from "@/components/ui/Section";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { SiteHeader } from "@/components/ghat/SiteHeader";
import { PageNav } from "@/components/ghat/PageNav";
import { QualitySummary } from "@/components/ghat/QualitySummary";
import { ReasonList } from "@/components/ghat/ReasonList";
import { ActionList } from "@/components/ghat/ActionList";
import { TargetChecklist } from "@/components/ghat/TargetChecklist";
import { DotPlot, type CriterionLine, type DotPoint, type MissingMark } from "@/components/ghat/DotPlot";
import { CoverageGrid } from "@/components/ghat/CoverageGrid";
import { cellTitle } from "@/components/ghat/ReadingMiniTable";
import { EvidenceTable, type EvidenceRowView } from "@/components/ghat/EvidenceTable";

export const dynamicParams = false;

export async function generateStaticParams() {
  const sites = await getRanking();
  return sites.map((s) => ({ siteId: s.siteId }));
}

export async function generateMetadata({ params }: PageProps<"/[lang]/ghats/[siteId]">): Promise<Metadata> {
  const { lang, siteId } = await params;
  const site = await getSite(siteId);
  if (!isLang(lang) || !site) return {};
  return { title: pick(site.name, lang) };
}

/** Display domain for a plot: covers the readings and every criterion line drawn on it. */
function domainFor(parameter: string, values: number[]): [number, number] {
  const hi = values.length ? Math.max(...values) : 0;
  const lo = values.length ? Math.min(...values) : 0;
  if (parameter === "pH") return [Math.min(6, Math.floor(lo * 2) / 2), Math.max(9.5, Math.ceil(hi * 2) / 2)];
  if (parameter === "BOD") return [0, Math.max(6, Math.ceil(hi * 1.1))];
  return [0, Math.max(8, Math.ceil(hi + 1))];
}

function criteriaFor(parameter: string, t: Dictionary): CriterionLine[] {
  const c = t.ghat.charts;
  if (parameter === "Dissolved oxygen")
    return [
      { value: 5, label: `${c.classB} ≥ 5`, kind: "standard" },
      { value: 4, label: `${c.classD} 4`, kind: "severity" },
    ];
  if (parameter === "BOD") return [{ value: 3, label: `${c.classB} ≤ 3`, kind: "standard" }];
  return [
    { value: 8.5, label: `${c.classB} 8.5`, kind: "standard" },
    { value: 6.5, label: `${c.classB} 6.5`, kind: "standard" },
  ];
}

function plotData(cells: GridCell[], parameter: string, seasonIndex: Map<string, number>, t: Dictionary) {
  const phaseIdx = { pre: 0, during: 1, after: 2 } as const;
  const slotOf = (c: GridCell) => (seasonIndex.get(`${c.year}|${c.festival}`) ?? 0) * 3 + phaseIdx[c.phase];
  const own = cells.filter((c) => c.parameter === parameter);
  const unit = own.find((c) => c.reading?.unitAssumed)?.reading?.unitAssumed ?? "";

  const points: DotPoint[] = own
    .filter(isUsable)
    .map((c) => ({
      slot: slotOf(c),
      value: c.reading!.value as number,
      title: fill(t.ghat.charts.dotTitle, {
        season: seasonLabel(c, t),
        phase: t.phase[c.phase],
        value: c.reading!.valueAsPrinted,
        unit,
        source: c.reading!.source ? `${refText(c.reading!.source, t)}, ${refStatus(c.reading!.source, t)}` : t.ghat.evidence.noPage,
      }).replace(/\s{2,}/g, " "),
    }));

  const missing: MissingMark[] = own
    .filter(isGap)
    .map((c) => ({
      slot: slotOf(c),
      short: t.valueStateShort[c.state],
      title: fill(t.ghat.charts.missingTitle, { season: seasonLabel(c, t), phase: t.phase[c.phase], state: cellTitle(c, t) }),
    }));

  return { points, missing, unit, domain: domainFor(parameter, points.map((p) => p.value)) };
}

export default async function GhatPage({ params }: PageProps<"/[lang]/ghats/[siteId]">) {
  const { lang, siteId } = await params;
  if (!isLang(lang)) notFound();
  const site = await getSite(siteId);
  const evidence = await getSiteEvidence(siteId);
  if (!site || !evidence) notFound();

  const t = getDictionary(lang);
  const [ranking, actions, standard] = await Promise.all([getRanking(), getRecommendedActions(siteId), getTargetStandard()]);

  const seasonIndex = new Map(evidence.seasons.map((s, i) => [`${s.year}|${s.festival}`, i]));
  const paramIndex = new Map(evidence.parameters.map((p, i) => [p, i]));
  const phaseIndex = new Map(evidence.phases.map((p, i) => [p, i]));
  const keySet = new Set<string>(KEY_PARAMETERS);

  const counts = {
    do: countStates(evidence.cells, "Dissolved oxygen"),
    bod: countStates(evidence.cells, "BOD"),
    ph: countStates(evidence.cells, "pH"),
  };

  const seasonLabels = evidence.seasons.map((s) => seasonLabel(s, t));
  const phaseLabels = evidence.phases.map((p) => t.phaseShort[p]);
  const plots = KEY_PARAMETERS.map((parameter) => {
    const data = plotData(evidence.cells, parameter, seasonIndex, t);
    const name = parameter === "Dissolved oxygen" ? t.ghat.charts.do : parameter === "BOD" ? t.ghat.charts.bod : t.ghat.charts.ph;
    return { parameter, name, ...data };
  });

  const rows: EvidenceRowView[] = evidence.cells.map((c) => ({
    key: c.key,
    seasonIdx: seasonIndex.get(`${c.year}|${c.festival}`) ?? 0,
    year: c.year,
    festival: c.festival,
    seasonText: seasonLabel(c, t),
    phase: c.phase,
    phaseIdx: phaseIndex.get(c.phase) ?? 0,
    phaseText: t.phase[c.phase],
    parameter: c.parameter,
    paramIdx: paramIndex.get(c.parameter) ?? 0,
    paramText: paramName(c.parameter, t),
    isKey: keySet.has(c.parameter),
    parameterAsPrinted: c.reading?.parameterAsPrinted ?? null,
    valueAsPrinted: c.reading?.valueAsPrinted ?? null,
    value: c.state === "numeric" ? (c.reading?.value ?? null) : null,
    unit: c.reading?.unitAssumed ?? "",
    state: c.state,
    stateText: t.valueState[c.state],
    short: t.valueStateShort[c.state],
    cellTitle: cellTitle(c, t),
    rawFlag: c.reading?.flag || null,
    criterion: criterionText(c.parameter, t),
    siteAsPrinted: c.reading?.siteAsPrinted ?? null,
    source: c.reading?.source ?? null,
    sourceText: c.reading?.source ? refText(c.reading.source, t) : null,
    sourceStatus: c.reading?.source ? refStatus(c.reading.source, t) : null,
    csvLine: c.reading?.csvLine ?? null,
  }));

  const s = t.ghat.sections;
  const e = t.ghat.evidence;

  return (
    <div className="flex flex-col gap-5">
      <SiteHeader site={site} siteCount={ranking.length} printedNames={evidence.printedNames} lang={lang} t={t} />

      <PageNav
        label={t.ghat.onThisPage}
        items={[
          { id: "summary", text: s.summary },
          { id: "reasons", text: s.reasons },
          { id: "actions", text: s.actions },
          { id: "charts", text: s.charts },
          { id: "coverage", text: s.coverage },
          { id: "evidence", text: s.evidence },
        ]}
      />

      <QualitySummary site={site} counts={counts} t={t} />

      <ReasonList site={site} cells={evidence.cells} printedNames={evidence.printedNames} lang={lang} t={t} />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] lg:items-start">
        <ActionList actions={actions} lang={lang} t={t} />
        <TargetChecklist standard={standard} lang={lang} t={t} />
      </div>

      <Section
        id="charts"
        title={t.ghat.charts.title}
        subtitle={t.ghat.charts.subtitle}
        aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="evidence.py" title={t.provenance.backendLong} />}
      >
        <div className="flex flex-col gap-6">
          <p aria-hidden className="no-print -mb-3 text-[11px] text-slate-500 sm:hidden">{t.ghat.charts.scrollHint}</p>
          {plots.map((p) => (
            <div key={p.parameter}>
              <h3 className="text-sm font-semibold text-slate-900">
                {p.name} <span className="font-normal text-slate-500">({p.unit || t.ghat.charts.unitNone})</span>
              </h3>
              <p className="mb-1 text-[11px] text-slate-500">{criterionText(p.parameter, t)}</p>
              <DotPlot
                id={`plot-${p.parameter.toLowerCase().replace(/\s+/g, "-")}`}
                title={`${p.name} — ${pick(site.name, lang)}`}
                description={fill(t.ghat.charts.aria, { param: p.name, site: pick(site.name, lang) })}
                unitLabel={p.unit || t.ghat.charts.unitNone}
                seasonLabels={seasonLabels}
                phaseLabels={phaseLabels}
                points={p.points}
                missing={p.missing}
                criteria={criteriaFor(p.parameter, t)}
                domain={p.domain}
                missingLabel={t.ghat.charts.missing}
              />
            </div>
          ))}
          <p className="text-[11px] text-slate-500">
            {t.ghat.charts.phaseKey}. {t.ghat.charts.caption}
          </p>
        </div>
      </Section>

      <CoverageGrid evidence={evidence} t={t} />

      <Section
        id="evidence"
        title={e.title}
        subtitle={e.subtitle}
        aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="evidence.py" title={t.provenance.backendLong} />}
      >
        <EvidenceTable
          rows={rows}
          labels={{
            filters: e.filters,
            col: e.col,
            showing: e.showing,
            empty: e.empty,
            noRow: e.noRow,
            noPage: e.noPage,
            flagLabel: e.flag,
            festivals: t.festival,
            phases: t.phase,
            parameters: evidence.parameters.map((p) => ({ value: p, text: paramName(p, t) })),
          }}
        />
      </Section>
    </div>
  );
}
