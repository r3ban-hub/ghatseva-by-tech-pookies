import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";
import type { FlagCode, GridCell, Lang, PrintedName, SiteRanking } from "@/lib/data/types";
import { fill, type Dictionary } from "@/lib/i18n";
import { FLAG_ORDER, FLAG_SEVERITY } from "@/lib/flags";
import { isGap } from "@/lib/evidence-view";
import { paramName, seasonLabel } from "@/lib/format";
import { Section } from "@/components/ui/Section";
import { FlagChip } from "@/components/data/FlagChip";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { SiteNoteList } from "@/components/overview/SiteNoteList";
import { ReadingMiniTable } from "./ReadingMiniTable";

interface Props {
  site: SiteRanking;
  cells: GridCell[];
  printedNames: PrintedName[];
  lang: Lang;
  t: Dictionary;
}

const DO_FLAGS: FlagCode[] = ["DO_SEVERE", "DO_ZERO", "DO_OFTEN_LOW"];
const KEY = new Set(["Dissolved oxygen", "BOD", "pH"]);

/** One entry per supplied flag: PRD sentence with denominators, notes with pages, expandable readings. */
export function ReasonList({ site, cells, printedNames, lang, t }: Props) {
  const r = t.ghat.reasons;
  const flags = FLAG_ORDER.filter((f) => site.flags.includes(f));
  const firstDoFlag = flags.find((f) => DO_FLAGS.includes(f));
  const byParam = (p: string) => cells.filter((c) => c.parameter === p);

  const sentence = (flag: FlagCode): string => {
    switch (flag) {
      case "DO_SEVERE":
        return fill(t.flagSentence.DO_SEVERE, { n: site.doBelow4, N: site.doBelow5.N, min: site.doMin });
      case "DO_ZERO":
        return fill(t.ghat.flagSentence.DO_ZERO, { n: site.doZeroCount });
      case "DO_OFTEN_LOW":
        return fill(t.flagSentence.DO_OFTEN_LOW, { n: site.doBelow5.n, N: site.doBelow5.N });
      case "BOD_OFTEN_HIGH":
        return fill(t.ghat.flagSentence.BOD_OFTEN_HIGH, { n: site.bodAbove3.n, N: site.bodAbove3.N });
      case "PH_OUT":
        return fill(t.ghat.flagSentence.PH_OUT, { n: site.phOutOfRange.n, N: site.phOutOfRange.N });
      case "DATA_GAP":
        return t.ghat.flagSentence.DATA_GAP;
      case "SITE_IDENTITY":
        return t.ghat.flagSentence.SITE_IDENTITY;
    }
  };

  const disclosure = (flag: FlagCode) => {
    if (flag === firstDoFlag) {
      const doCells = byParam("Dissolved oxygen");
      return <Reveal summary={fill(r.showReadings, { param: paramName("Dissolved oxygen", t), n: doCells.length })}><ReadingMiniTable cells={doCells} t={t} /></Reveal>;
    }
    if (flag === "BOD_OFTEN_HIGH") {
      const c = byParam("BOD");
      return <Reveal summary={fill(r.showReadings, { param: "BOD", n: c.length })}><ReadingMiniTable cells={c} t={t} /></Reveal>;
    }
    if (flag === "PH_OUT") {
      const c = byParam("pH");
      return <Reveal summary={fill(r.showReadings, { param: "pH", n: c.length })}><ReadingMiniTable cells={c} t={t} /></Reveal>;
    }
    if (flag === "DATA_GAP") {
      const c = cells.filter((x) => KEY.has(x.parameter) && isGap(x));
      return <Reveal summary={fill(r.showMissing, { n: c.length })}><ReadingMiniTable cells={c} t={t} showParameter /></Reveal>;
    }
    if (flag === "SITE_IDENTITY") {
      return (
        <Reveal summary={fill(r.showNames, { n: printedNames.length })}>
          <ul className="mt-2 space-y-1 text-xs">
            {printedNames.map((p) => (
              <li key={p.name}>
                <span className="font-medium text-slate-900">“{p.name}”</span>{" "}
                <span className="text-slate-500">{p.seasons.map((s) => seasonLabel(s, t)).join(", ")}</span>
              </li>
            ))}
          </ul>
        </Reveal>
      );
    }
    return null;
  };

  return (
    <Section id="reasons" title={r.title} subtitle={r.subtitle}>
      <ol className="divide-y divide-slate-100">
        {flags.map((flag) => (
          <li key={flag} className="py-3 first:pt-1 last:pb-1">
            <div className="flex flex-wrap items-center gap-2">
              <FlagChip severity={FLAG_SEVERITY[flag]} label={t.flag[flag].short} title={t.flag[flag].long} identity={flag === "SITE_IDENTITY"} />
              <ProvenanceTag provenance="backend" label={t.provenance.backend} detail="ranking.py" title={t.provenance.backendLong} />
            </div>
            <p className="mt-1.5 text-sm text-slate-800">{sentence(flag)}</p>
            <SiteNoteList
              notes={site.notes.filter((n) => n.flag === flag)}
              lang={lang}
              t={t}
              refsOnly={["DO_SEVERE", "DO_OFTEN_LOW", "BOD_OFTEN_HIGH", "PH_OUT", "SITE_IDENTITY"]}
              provenanceTag={false}
            />
            {disclosure(flag)}
          </li>
        ))}
      </ol>
    </Section>
  );
}

function Reveal({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="group mt-2 rounded border border-slate-200 bg-slate-50/60 px-3 py-1.5">
      <summary className="flex cursor-pointer list-none items-center gap-1 text-xs font-medium text-accent select-none hover:text-accent-strong">
        <ChevronRight aria-hidden className="h-3.5 w-3.5 transition-transform group-open:rotate-90" />
        {summary}
      </summary>
      {children}
    </details>
  );
}
