import type { HeadlineFinding, Lang } from "@/lib/data/types";
import { fill, pick, type Dictionary } from "@/lib/i18n";
import { Section } from "@/components/ui/Section";
import { FractionBar } from "@/components/data/FractionBar";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { SourceRefLink } from "@/components/data/SourceRefLink";

/** Compact list of PRD-stated counts with their denominators. No oversized KPI cards. */
export function HeadlineFindings({ items, lang, t }: { items: HeadlineFinding[]; lang: Lang; t: Dictionary }) {
  const h = t.overview.headlines;
  return (
    <Section id="findings" title={h.title} subtitle={h.subtitle}>
      <ul className="divide-y divide-slate-100">
        {items.map((f) => {
          const isCaveat = f.emphasis === "caveat";
          return (
            <li
              key={f.id}
              className={`grid gap-x-4 gap-y-1 py-2.5 sm:grid-cols-[minmax(0,1.3fr)_auto_minmax(0,1.6fr)] sm:items-center ${
                isCaveat ? "-mx-4 border-l-4 border-navy bg-navy-soft/60 px-4" : ""
              }`}
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900">{pick(f.label, lang)}</p>
                <div className="mt-0.5">
                  <ProvenanceTag provenance={f.provenance} label={t.provenance[f.provenance]} detail={f.prdRef.replace("PRD v2 ", "")} title={f.provenance === "backend" ? t.provenance.backendLong : t.provenance.prdLong} />
                </div>
              </div>
              <div className="sm:justify-self-end">
                {f.value.kind === "fraction" ? (
                  <FractionBar
                    value={f.value.value}
                    text={fill(h.ofReadings, { n: f.value.value.n, N: f.value.value.N })}
                    width="w-24"
                  />
                ) : (
                  <span className="text-lg font-semibold text-slate-900 tabular-nums">{fill(h.readings, { n: f.value.value })}</span>
                )}
              </div>
              <div className="min-w-0 text-xs text-slate-600">
                {f.detail && <p>{pick(f.detail, lang)}</p>}
                {f.refs && f.refs.length > 0 && (
                  <p className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                    {f.refs.map((r) => (
                      <SourceRefLink
                        key={`${r.year}-${r.page}`}
                        source={r}
                        text={fill(t.source.report, { year: r.year, page: r.page })}
                        statusText={r.verified ? t.source.verified : t.source.unverified}
                      />
                    ))}
                  </p>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </Section>
  );
}
