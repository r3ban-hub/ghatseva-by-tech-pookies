import Link from "next/link";
import { ChevronLeft, HelpCircle, MapPin, Tag } from "lucide-react";
import type { Lang, PrintedName, SiteRanking } from "@/lib/data/types";
import { fill, pick, type Dictionary } from "@/lib/i18n";
import { seasonLabel } from "@/lib/format";
import { screenHref } from "@/lib/screens";
import { TierBadge } from "@/components/data/TierBadge";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";

interface Props {
  site: SiteRanking;
  siteCount: number;
  printedNames: PrintedName[];
  lang: Lang;
  t: Dictionary;
}

export function SiteHeader({ site, siteCount, printedNames, lang, t }: Props) {
  const h = t.ghat.header;
  const medium = site.identityConfidence !== "high";

  return (
    <header className="flex flex-col gap-3">
      <Link
        href={screenHref(lang, "overview", "#ranking")}
        className="no-print inline-flex w-fit items-center gap-1 text-sm text-slate-600 hover:text-navy hover:underline"
      >
        <ChevronLeft aria-hidden className="h-4 w-4" />
        {t.ghat.back}
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
            {fill(t.ghat.rankOf, { rank: site.rank, N: siteCount })}
          </p>
          <h1 className="mt-0.5 text-2xl font-semibold tracking-tight text-slate-900">{pick(site.name, lang)}</h1>
          {lang === "hi" && <p className="text-sm text-slate-500">{site.name.en}</p>}
          <p className="mt-1 inline-flex items-center gap-1.5 text-sm text-slate-700">
            <MapPin aria-hidden className="h-4 w-4 text-slate-400" />
            <span className="text-slate-500">{h.waterBody}:</span> {pick(site.waterBody, lang)}
          </p>
        </div>
        <div className="flex flex-col items-start gap-1.5 sm:items-end">
          <div className="flex items-center gap-2">
            <TierBadge tier={site.tier} label={fill(t.tier.label, { n: site.tier })} title={t.tier[site.tier]} />
            {site.highRisk && (
              <span className="rounded border border-risk-red-line bg-white px-1.5 py-0.5 text-xs font-semibold tracking-wide text-risk-red uppercase">
                {t.overview.ranking.highRisk}
              </span>
            )}
          </div>
          <p className="max-w-xs text-xs text-slate-600 sm:text-right">{t.tier[site.tier]}</p>
          <ProvenanceTag provenance={site.provenance} label={t.provenance[site.provenance]} detail="ranking.py" title={t.provenance.backendLong} />
        </div>
      </div>

      <div
        className={`rounded-md border px-4 py-3 ${medium ? "hatch border-slate-400 bg-missing-bg" : "border-slate-200 bg-white"}`}
      >
        <p className="flex items-center gap-1.5 text-sm text-slate-900">
          {medium ? (
            <HelpCircle aria-hidden className="h-4 w-4 text-slate-600" />
          ) : (
            <Tag aria-hidden className="h-4 w-4 text-slate-500" />
          )}
          <span className="font-medium">{h.identity}:</span> {medium ? h.identityMedium : h.identityHigh}
        </p>
        <details className="mt-1.5 text-xs text-slate-700" open={medium}>
          <summary className="cursor-pointer font-medium text-slate-700 hover:text-navy">
            {h.printedNames} ({printedNames.length})
          </summary>
          <ul className="mt-1.5 space-y-1">
            {printedNames.map((p) => (
              <li key={p.name} className="flex flex-wrap gap-x-2">
                <span className="font-medium text-slate-900">“{p.name}”</span>
                <span className="text-slate-500">{p.seasons.map((s) => seasonLabel(s, t)).join(", ")}</span>
              </li>
            ))}
          </ul>
          <p className="mt-1.5 flex flex-wrap items-center gap-2 text-slate-500">
            {h.printedNamesNote}
            <ProvenanceTag provenance="backend" label={t.provenance.backend} detail="evidence.py" title={t.provenance.backendLong} />
          </p>
        </details>
      </div>
    </header>
  );
}
