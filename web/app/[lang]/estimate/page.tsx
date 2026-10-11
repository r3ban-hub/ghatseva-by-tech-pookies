import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getEstimateLines } from "@/lib/data";
import { getDictionary, isLang, pick } from "@/lib/i18n";
import { Section } from "@/components/ui/Section";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { Estimator } from "@/components/estimate/Estimator";

export async function generateMetadata({ params }: PageProps<"/[lang]/estimate">): Promise<Metadata> {
  const { lang } = await params;
  return isLang(lang) ? { title: getDictionary(lang).estimate.title } : {};
}

export default async function EstimatePage({ params }: PageProps<"/[lang]/estimate">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const t = getDictionary(lang);
  const e = t.estimate;
  const lines = await getEstimateLines();

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{e.title}</h1>
        <p className="max-w-3xl text-sm text-slate-600">{e.intro}</p>
      </header>

      <Section
        subtitle={e.sourceNote}
        aside={
          <div className="flex flex-wrap gap-1">
            <ProvenanceTag provenance="blank" label={t.provenance.blank} title={t.provenance.blankLong} />
          </div>
        }
      >
        <Estimator
          lines={lines.map((l) => ({ id: l.id, item: pick(l.item, lang), unit: pick(l.unit, lang) }))}
          labels={e}
        />
        <p className="mt-3 text-xs text-slate-600">{e.notInBrief}</p>
      </Section>
    </div>
  );
}
