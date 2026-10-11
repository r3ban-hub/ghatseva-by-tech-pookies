import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import type { Fraction, SiteRanking } from "@/lib/data/types";
import { fill, type Dictionary } from "@/lib/i18n";
import type { StateCounts } from "@/lib/evidence-view";
import { Section } from "@/components/ui/Section";
import { FractionBar } from "@/components/data/FractionBar";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";

interface Props {
  site: SiteRanking;
  counts: { do: StateCounts; bod: StateCounts; ph: StateCounts };
  t: Dictionary;
}

interface Row {
  label: string;
  value: ReactNode;
}

/** DO / BOD / pH cards. Counts come from PRD v2 §6.5; the transcription breakdown shows coverage. */
export function QualitySummary({ site, counts, t }: Props) {
  const s = t.ghat.summary;
  const frac = (f: Fraction) => (
    <FractionBar value={f} text={fill(t.overview.headlines.ofReadings, { n: f.n, N: f.N })} width="w-16" />
  );

  const cards: { key: "do" | "bod" | "ph"; title: string; standard: string; prdN: number; rows: Row[] }[] = [
    {
      key: "do",
      title: t.ghat.charts.do,
      standard: t.ghat.criterion.do,
      prdN: site.doBelow5.N,
      rows: [
        { label: s.below5, value: frac(site.doBelow5) },
        { label: s.below4, value: <Num n={site.doBelow4} risk={site.doBelow4 > 0} /> },
        { label: s.zero, value: <Num n={site.doZeroCount} risk={site.doZeroCount > 0} /> },
        { label: s.lowest, value: <span className="font-medium text-slate-900 tabular-nums">{site.doMin} mg/l</span> },
      ],
    },
    {
      key: "bod",
      title: t.ghat.charts.bod,
      standard: t.ghat.criterion.bod,
      prdN: site.bodAbove3.N,
      rows: [{ label: s.above3, value: frac(site.bodAbove3) }],
    },
    {
      key: "ph",
      title: t.ghat.charts.ph,
      standard: t.ghat.criterion.ph,
      prdN: site.phOutOfRange.N,
      rows: [{ label: s.outside, value: frac(site.phOutOfRange) }],
    },
  ];

  return (
    <Section
      id="summary"
      title={s.title}
      subtitle={s.subtitle}
      aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="ranking.py" title={t.provenance.backendLong} />}
    >
      <div className="grid gap-3 md:grid-cols-3">
        {cards.map((card) => {
          const c = counts[card.key];
          const mismatch = c.numeric !== card.prdN;
          return (
            <div key={card.key} className="rounded border border-slate-200 px-3 py-2.5">
              <h3 className="text-sm font-semibold text-slate-900">{card.title}</h3>
              <p className="text-[11px] text-slate-500">
                {s.standard}: {card.standard}
              </p>
              <dl className="mt-2 space-y-1.5 text-xs">
                {card.rows.map((row) => (
                  <div key={row.label} className="flex items-center justify-between gap-3">
                    <dt className="text-slate-600">{row.label}</dt>
                    <dd>{row.value}</dd>
                  </div>
                ))}
              </dl>
              <div className="mt-2.5 border-t border-slate-100 pt-2 text-[11px] text-slate-600">
                <p className="font-medium text-slate-700">{s.available}</p>
                <p className="mt-0.5">
                  {fill(s.breakdown, {
                    numeric: c.numeric,
                    notSampled: c.not_sampled,
                    noTable: c.no_table,
                    expected: c.expected,
                  })}
                </p>
                {c.unknown_flag > 0 && (
                  <p className="mt-0.5">
                    {t.valueState.unknown_flag}: {c.unknown_flag}
                  </p>
                )}
                {mismatch && (
                  <p className="mt-1 flex items-start gap-1 font-medium text-risk-amber">
                    <AlertTriangle aria-hidden className="mt-0.5 h-3 w-3 shrink-0" />
                    {fill(s.mismatch, { n: c.numeric, N: card.prdN })}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </Section>
  );
}

function Num({ n, risk }: { n: number; risk: boolean }) {
  return <span className={`font-medium tabular-nums ${risk ? "text-risk-red" : "text-slate-500"}`}>{n}</span>;
}
