import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronRight, FileText } from "lucide-react";
import { getRanking, getRecommendedActions } from "@/lib/data";
import { fill, getDictionary, isLang, pick } from "@/lib/i18n";
import { FLAG_ORDER, FLAG_SEVERITY } from "@/lib/flags";
import { Section } from "@/components/ui/Section";
import { TierBadge } from "@/components/data/TierBadge";
import { FlagChip } from "@/components/data/FlagChip";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";

export async function generateMetadata({ params }: PageProps<"/[lang]/orders">): Promise<Metadata> {
  const { lang } = await params;
  return isLang(lang) ? { title: getDictionary(lang).orders.title } : {};
}

export default async function OrdersPage({ params }: PageProps<"/[lang]/orders">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const t = getDictionary(lang);
  const o = t.orders;
  const sites = await getRanking();
  const counts = await Promise.all(sites.map((s) => getRecommendedActions(s.siteId).then((a) => a.length)));

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-1.5">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{o.title}</h1>
        <p className="max-w-3xl text-sm text-slate-600">{o.intro}</p>
      </header>
      <p className="hatch rounded border border-dashed border-slate-500 bg-white px-3 py-2 text-xs font-semibold text-slate-900">{o.draft}</p>

      <Section
        title={t.common.allGhats}
        aside={<ProvenanceTag provenance="backend" label={t.provenance.backend} detail="orders.py" title={t.provenance.backendLong} />}
      >
        <ul className="divide-y divide-slate-100">
          {sites.map((s, i) => (
            <li key={s.siteId} className="flex flex-wrap items-start gap-x-4 gap-y-2 py-3 sm:flex-nowrap">
              <span className="w-6 shrink-0 text-right text-base font-semibold text-slate-900 tabular-nums">{s.rank}</span>
              <div className="min-w-0 flex-1">
                <p className="font-medium text-slate-900">{pick(s.name, lang)}</p>
                <p className="text-xs text-slate-500">
                  {pick(s.waterBody, lang)} · {t.orders.zone}: {t.common.assignBlank} · {counts[i]} {o.tasks.toLowerCase()}
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {FLAG_ORDER.filter((f) => s.flags.includes(f)).map((f) => (
                    <FlagChip key={f} severity={FLAG_SEVERITY[f]} label={t.flag[f].short} identity={f === "SITE_IDENTITY"} />
                  ))}
                </div>
              </div>
              <div className="flex w-full items-center justify-between gap-4 pl-10 sm:w-auto sm:shrink-0 sm:self-center sm:pl-0">
                <div className="flex items-center gap-2 sm:w-36">
                  <TierBadge tier={s.tier} label={fill(t.tier.label, { n: s.tier })} title={t.tier[s.tier]} />
                  {s.highRisk && <span className="text-[11px] font-semibold tracking-wide whitespace-nowrap text-risk-red uppercase">{t.overview.ranking.highRisk}</span>}
                </div>
                <Link
                  href={`/${lang}/orders/${s.siteId}/`}
                  className="inline-flex shrink-0 items-center gap-1 rounded border border-slate-300 bg-white px-2.5 py-1 text-sm text-slate-800 hover:border-navy hover:text-navy"
                >
                  <FileText aria-hidden className="h-4 w-4" />
                  {o.open}
                  <ChevronRight aria-hidden className="h-4 w-4" />
                </Link>
              </div>
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
