import Link from "next/link";
import { CircleDashed, HelpCircle } from "lucide-react";
import type { Lang, Meta, SiteRanking } from "@/lib/data/types";
import { fill, pick, type Dictionary } from "@/lib/i18n";
import { ghatHref } from "@/lib/screens";
import { Section } from "@/components/ui/Section";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { SiteNoteList } from "./SiteNoteList";

/** DATA_GAP and SITE_IDENTITY notes, plus the expected-grid summary. Missing is shown as missing. */
export function DataGaps({ sites, meta, lang, t }: { sites: SiteRanking[]; meta: Meta; lang: Lang; t: Dictionary }) {
  const g = t.overview.gaps;
  const withGaps = sites.filter((s) => s.flags.includes("DATA_GAP") || s.flags.includes("SITE_IDENTITY"));

  return (
    <Section title={g.title} subtitle={g.subtitle}>
      <div className="hatch -mx-1 mb-3 rounded border border-slate-300 bg-missing-bg px-3 py-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-semibold text-slate-900">{g.coverageTitle}</p>
          <ProvenanceTag provenance={meta.coverage.provenance} label={t.provenance[meta.coverage.provenance]} detail={meta.coverage.prdRef} title={t.provenance.backendLong} />
        </div>
        <p className="mt-1 text-xs text-slate-800">
          {fill(g.coverageBody, {
            expected: meta.coverage.expectedCells.toLocaleString("en-IN"),
            rows: meta.coverage.rowsInFile.toLocaleString("en-IN"),
            absent: meta.coverage.absentCells,
          })}
        </p>
        <p className="mt-1 text-xs text-slate-700">{pick(meta.coverage.absentDetail, lang)}</p>
      </div>

      <ul className="divide-y divide-slate-100">
        {withGaps.map((s) => {
          const notes = s.notes.filter((n) => n.flag === "DATA_GAP" || n.flag === "SITE_IDENTITY");
          const identity = s.flags.includes("SITE_IDENTITY");
          const Icon = identity ? HelpCircle : CircleDashed;
          return (
            <li key={s.siteId} className="py-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <Icon aria-hidden className="h-4 w-4 text-slate-500" />
                <span className="text-xs font-semibold text-slate-500 tabular-nums">#{s.rank}</span>
                <Link href={ghatHref(lang, s.siteId)} className="text-sm font-semibold text-slate-900 hover:text-navy hover:underline">
                  {pick(s.name, lang)}
                </Link>
                {s.flags.includes("DATA_GAP") && <span className="text-[11px] text-slate-600">{t.flag.DATA_GAP.short}</span>}
                {identity && <span className="text-[11px] text-slate-600">{t.flag.SITE_IDENTITY.short}</span>}
              </div>
              <SiteNoteList notes={notes} lang={lang} t={t} />
            </li>
          );
        })}
      </ul>
    </Section>
  );
}
