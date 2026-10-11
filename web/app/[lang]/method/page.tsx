import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AlertTriangle } from "lucide-react";
import type { CellState } from "@/lib/data/types";
import { getMeta } from "@/lib/data";
import { fill, getDictionary, isLang, pick } from "@/lib/i18n";
import { Section } from "@/components/ui/Section";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { OverviewLegend } from "@/components/overview/OverviewLegend";
import { CellValue } from "@/components/ghat/CellValue";

export async function generateMetadata({ params }: PageProps<"/[lang]/method">): Promise<Metadata> {
  const { lang } = await params;
  return isLang(lang) ? { title: getDictionary(lang).method.title } : {};
}

const STATES: CellState[] = ["numeric", "bdl", "nd", "not_sampled", "no_table", "unknown_flag", "invalid_value"];
const STATE_RULE: Record<CellState, { en: string; hi: string }> = {
  numeric: { en: "A printed number, including 0. Counted as a reading.", hi: "छपी संख्या, 0 सहित। रीडिंग के रूप में गिनी जाती है।" },
  bdl: { en: "Below detection limit: very low, not zero and not missing. Occurs only for metals here.", hi: "पहचान सीमा से कम: बहुत कम, शून्य नहीं और अनुपलब्ध नहीं। यहाँ केवल धातुओं में।" },
  nd: { en: "Not detected: very low. Not present in the Bhopal file.", hi: "पता नहीं चला: बहुत कम। भोपाल फ़ाइल में नहीं है।" },
  not_sampled: { en: "Blank, _, -, * or ** in the report. Missing; never counted as passing.", hi: "रिपोर्ट में खाली, _, -, * या **। अनुपलब्ध; कभी पास नहीं गिना जाता।" },
  no_table: { en: "Expected cell with no row in the CSV (table or parameter absent from the report). Missing; never counted as passing.", hi: "अपेक्षित सेल जिसकी CSV में पंक्ति नहीं (रिपोर्ट में तालिका या पैरामीटर नहीं)। अनुपलब्ध; कभी पास नहीं गिना जाता।" },
  unknown_flag: { en: "Any other flag. Shown as printed with “meaning unresolved”.", hi: "कोई अन्य फ़्लैग। जैसा छपा वैसा, “अर्थ अनसुलझा” के साथ।" },
  invalid_value: { en: "A printed number that cannot be a real reading (negative). Reported as a data issue; never compared or counted as passing.", hi: "छपी संख्या जो असली रीडिंग नहीं हो सकती (ऋणात्मक)। डेटा समस्या के रूप में दर्ज; कभी तुलना या पास नहीं।" },
};
const SAMPLE: Partial<Record<CellState, string>> = { numeric: "6.4", bdl: "BDL", nd: "ND" };

export default async function MethodPage({ params }: PageProps<"/[lang]/method">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const t = getDictionary(lang);
  const m = t.method;
  const meta = await getMeta();

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{m.title}</h1>
        <p className="max-w-3xl text-sm text-slate-600">{m.intro}</p>
      </header>

      <section aria-labelledby="discrepancy" className="rounded-md border border-risk-amber-line bg-risk-amber-bg px-4 py-3">
        <h2 id="discrepancy" className="flex items-center gap-1.5 text-sm font-semibold text-risk-amber">
          <AlertTriangle aria-hidden className="h-4 w-4" />
          {m.discrepancyTitle}
        </h2>
        <p className="mt-1 text-sm text-slate-800">{m.discrepancyBody}</p>
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section
          title={m.criteria}
          subtitle={m.criteriaBody}
          aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="criteria CSV" title={t.provenance.backendLong} />}
        >
          <table className="w-full text-sm">
            <tbody>
              {meta.criteria.map((c) => (
                <tr key={`${c.cpcbClass}-${pick(c.parameter, "en")}`} className="border-b border-slate-100 last:border-0">
                  <th scope="row" className="py-1.5 pr-3 text-left font-medium text-slate-900">{pick(c.parameter, lang)}</th>
                  <td className="py-1.5 pr-3 text-slate-600">Class {c.cpcbClass}</td>
                  <td className="py-1.5 text-slate-800">{pick(c.rule, lang)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-slate-700">{m.classD}</p>
          <p className="hatch mt-2 rounded border border-slate-300 bg-missing-bg px-3 py-2 text-xs text-slate-800">{pick(meta.notAssessable, lang)}</p>
        </Section>

        <Section
          title={m.ranking}
          aside={<ProvenanceTag provenance="prd" label={t.provenance.prd} detail="§6.3–6.4" title={t.provenance.prdLong} />}
        >
          <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-800">
            {m.rankingSteps.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
          <p className="mt-2 text-xs text-slate-700">{m.whyDo}</p>
          <p className="mt-2 border-l-4 border-navy bg-navy-soft/60 px-3 py-2 text-xs text-slate-800">{m.highRisk}</p>
        </Section>
      </div>

      <Section title={m.states} subtitle={m.statesBody}>
        <ul className="grid gap-2 md:grid-cols-2">
          {STATES.map((s) => (
            <li key={s} className="flex items-start gap-2 text-xs">
              <CellValue state={s} printed={SAMPLE[s]} short={t.valueStateShort[s] || "6.4"} title={t.valueState[s]} compact />
              <span>
                <span className="font-medium text-slate-900">{t.valueState[s]}.</span> {pick(STATE_RULE[s], lang)}
              </span>
            </li>
          ))}
        </ul>
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title={m.coverage} aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="load.py" title={t.provenance.backendLong} />}>
          <p className="text-sm text-slate-800">
            {fill(t.overview.gaps.coverageBody, {
              expected: meta.coverage.expectedCells.toLocaleString("en-IN"),
              rows: meta.coverage.rowsInFile.toLocaleString("en-IN"),
              absent: meta.coverage.absentCells,
            })}
          </p>
          <p className="mt-1 text-xs text-slate-700">{pick(meta.coverage.absentDetail, lang)}</p>
          <p className="mt-2 text-xs text-slate-600">
            {pick(meta.dataWindow, lang)} ·{" "}
            <a href={meta.trackRepoUrl} className="text-accent underline underline-offset-2">
              {m.dataPack}
            </a>
          </p>
        </Section>

        <Section title={m.limits}>
          <ul className="list-disc space-y-1 pl-5 text-xs text-slate-800">
            {m.limitItems.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
        </Section>
      </div>

      <OverviewLegend t={t} />
    </div>
  );
}
