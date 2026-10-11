import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import type { Lang, SiteRanking } from "@/lib/data/types";
import { fill, pick, type Dictionary } from "@/lib/i18n";
import { ghatHref } from "@/lib/screens";
import { Section } from "@/components/ui/Section";
import { TierBadge } from "@/components/data/TierBadge";
import { SiteNoteList } from "./SiteNoteList";

/** Ghats carrying the DO_SEVERE flag (supplied by the data), in official rank order. */
export function CriticalFlags({ sites, lang, t }: { sites: SiteRanking[]; lang: Lang; t: Dictionary }) {
  const critical = sites.filter((s) => s.flags.includes("DO_SEVERE"));
  const c = t.overview.critical;

  return (
    <Section title={c.title} subtitle={c.subtitle}>
      <ol className="divide-y divide-slate-100">
        {critical.map((s) => {
          const notes = s.notes.filter((n) => n.flag === "DO_SEVERE" || n.flag === "DO_ZERO");
          return (
            <li key={s.siteId} className="py-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <AlertTriangle aria-hidden className="h-4 w-4 text-risk-red" />
                <span className="text-xs font-semibold text-slate-500 tabular-nums">#{s.rank}</span>
                <Link href={ghatHref(lang, s.siteId)} className="text-sm font-semibold text-slate-900 hover:text-navy hover:underline">
                  {pick(s.name, lang)}
                </Link>
                <TierBadge tier={s.tier} label={fill(t.tier.label, { n: s.tier })} title={t.tier[s.tier]} />
              </div>
              <p className="mt-1 text-sm text-slate-800">
                {fill(t.flagSentence.DO_SEVERE, { n: s.doBelow4, N: s.doBelow5.N, min: s.doMin })}
                {s.flags.includes("DO_OFTEN_LOW") && (
                  <> {fill(t.flagSentence.DO_OFTEN_LOW, { n: s.doBelow5.n, N: s.doBelow5.N })}</>
                )}
              </p>
              <SiteNoteList notes={notes} lang={lang} t={t} refsOnly={["DO_SEVERE"]} />
            </li>
          );
        })}
      </ol>
    </Section>
  );
}
