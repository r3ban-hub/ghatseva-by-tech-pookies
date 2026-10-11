import type { ReactNode } from "react";
import type { Lang, Meta } from "@/lib/data/types";
import { fill, pick, type Dictionary } from "@/lib/i18n";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";

export function ScopeBar({ meta, lang, t }: { meta: Meta; lang: Lang; t: Dictionary }) {
  const s = t.overview.scope;
  const standards = meta.criteria.filter((c) => c.role === "standard");
  const severity = meta.criteria.find((c) => c.role === "severity_line");

  const items: { term: string; value: ReactNode }[] = [
    { term: s.data, value: pick(meta.dataWindow, lang) },
    { term: s.ghats, value: fill(s.ghatsValue, { n: meta.ghatCount }) },
    {
      term: s.standard,
      value: (
        <>
          <span className="font-medium text-slate-900">{s.classB}:</span>{" "}
          {standards.map((c) => `${pick(c.parameter, lang)} ${pick(c.rule, lang)}`).join(" · ")}
          {severity && (
            <span className="block text-slate-500">
              {pick(severity.parameter, lang)}, CPCB Class {severity.cpcbClass}: {pick(severity.rule, lang)}
            </span>
          )}
        </>
      ),
    },
    { term: s.notAssessable, value: pick(meta.notAssessable, lang) },
    { term: s.pages, value: s.pagesValue },
  ];

  return (
    <section aria-label={s.title} className="rounded-md border border-slate-200 bg-white px-4 py-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xs font-semibold tracking-wide text-slate-500 uppercase">{s.title}</h2>
        <ProvenanceTag provenance="backend" label={t.provenance.backend} detail="load.py, criteria.py" title={t.provenance.backendLong} />
      </div>
      <dl className="grid gap-x-6 gap-y-2 text-xs sm:grid-cols-2 lg:grid-cols-[repeat(5,minmax(0,auto))]">
        {items.map((it) => (
          <div key={it.term} className="min-w-0">
            <dt className="font-medium text-slate-500">{it.term}</dt>
            <dd className="mt-0.5 text-slate-800">{it.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
