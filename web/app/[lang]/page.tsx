import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getHeadlines, getMeta, getRanking } from "@/lib/data";
import { fill, getDictionary, isLang, pick } from "@/lib/i18n";
import { FLAG_ORDER, FLAG_SEVERITY } from "@/lib/flags";
import { ghatHref } from "@/lib/screens";
import { Section } from "@/components/ui/Section";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { ScopeBar } from "@/components/overview/ScopeBar";
import { HeadlineFindings } from "@/components/overview/HeadlineFindings";
import { RankingTable, type RankingRowView } from "@/components/overview/RankingTable";
import { CriticalFlags } from "@/components/overview/CriticalFlags";
import { DataGaps } from "@/components/overview/DataGaps";
import { OverviewLegend } from "@/components/overview/OverviewLegend";

export async function generateMetadata({ params }: PageProps<"/[lang]">): Promise<Metadata> {
  const { lang } = await params;
  if (!isLang(lang)) return {};
  return { title: getDictionary(lang).overview.title };
}

export default async function OverviewPage({ params }: PageProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const t = getDictionary(lang);
  const [meta, sites, headlines] = await Promise.all([getMeta(), getRanking(), getHeadlines()]);
  const r = t.overview.ranking;

  // Prepare display strings on the server; the client table only sorts and filters them.
  const rows: RankingRowView[] = sites.map((s) => {
    const coverage = [
      { key: "do" as const, numeric: s.doBelow5.N },
      { key: "bod" as const, numeric: s.bodAbove3.N },
      { key: "ph" as const, numeric: s.phOutOfRange.N },
    ].map(({ key, numeric }) => ({
      param: t.params[key],
      numeric,
      expected: s.expectedPerParameter,
      title: fill(r.coverageTitle, {
        param: t.params[key],
        n: numeric,
        N: s.expectedPerParameter,
        m: s.expectedPerParameter - numeric,
      }),
    }));

    return {
      siteId: s.siteId,
      href: ghatHref(lang, s.siteId),
      rank: s.rank,
      tier: s.tier,
      tierLabel: fill(t.tier.label, { n: s.tier }),
      tierTitle: t.tier[s.tier],
      highRisk: s.highRisk,
      name: pick(s.name, lang),
      nameSecondary: lang === "hi" ? s.name.en : undefined,
      waterBody: pick(s.waterBody, lang),
      identityMedium: s.identityConfidence !== "high",
      doBelow5: s.doBelow5,
      doBelow5Label: fill(t.flagSentence.DO_OFTEN_LOW, { n: s.doBelow5.n, N: s.doBelow5.N }),
      doBelow4: s.doBelow4,
      doMin: s.doMin,
      bodAbove3: s.bodAbove3,
      bodAbove3Label: `${t.overview.ranking.col.bodAbove3}: ${fill(t.overview.headlines.ofReadings, { n: s.bodAbove3.n, N: s.bodAbove3.N })}`,
      phOut: s.phOutOfRange,
      phOutLabel: `${t.overview.ranking.col.phOut}: ${fill(t.overview.headlines.ofReadings, { n: s.phOutOfRange.n, N: s.phOutOfRange.N })}`,
      coverage,
      flags: FLAG_ORDER.filter((code) => s.flags.includes(code)).map((code) => ({
        code,
        severity: FLAG_SEVERITY[code],
        label: t.flag[code].short,
        title: t.flag[code].long,
      })),
      openLabel: fill(r.open, { name: pick(s.name, lang) }),
    };
  });

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{t.overview.title}</h1>
        <p className="max-w-3xl text-sm text-slate-600">{t.overview.intro}</p>
      </header>

      <ScopeBar meta={meta} lang={lang} t={t} />

      <Section
        id="ranking"
        title={r.title}
        subtitle={r.subtitle}
        aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="ranking.py" title={t.provenance.backendLong} />}
      >
        <RankingTable
          rows={rows}
          labels={{
            col: r.col,
            unitMgL: r.unitMgL,
            sortBy: r.sortBy,
            highRisk: r.highRisk,
            identityMedium: r.identityMedium,
            filterAll: r.filterAll,
            filterHigh: r.filterHigh,
            showing: r.showing,
            empty: r.empty,
          }}
        />
      </Section>

      <div id="flags" className="grid scroll-mt-4 gap-5 lg:grid-cols-2">
        <CriticalFlags sites={sites} lang={lang} t={t} />
        <DataGaps sites={sites} meta={meta} lang={lang} t={t} />
      </div>

      <HeadlineFindings items={headlines} lang={lang} t={t} />

      <OverviewLegend t={t} />
    </div>
  );
}
