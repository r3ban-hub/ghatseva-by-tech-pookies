import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import {
  getRanking,
  getRecommendedActions,
  getSite,
  getSiteEvidence,
  getTargetStandard,
  getTaskGroups,
  getWorkOrderMeta,
} from "@/lib/data";
import { fill, getDictionary, isLang, pick } from "@/lib/i18n";
import { siteReasons } from "@/lib/reasons";
import { WorkOrder } from "@/components/orders/WorkOrder";
import { CopyTextButton, PrintButton } from "@/components/ui/DocActions";

export const dynamicParams = false;

export async function generateStaticParams() {
  const sites = await getRanking();
  return sites.map((s) => ({ siteId: s.siteId }));
}

export async function generateMetadata({ params }: PageProps<"/[lang]/orders/[siteId]">): Promise<Metadata> {
  const { lang, siteId } = await params;
  const site = await getSite(siteId);
  if (!isLang(lang) || !site) return {};
  return { title: `${getDictionary(lang).orders.orderTitle} — ${pick(site.name, lang)}` };
}

export default async function OrderPage({ params }: PageProps<"/[lang]/orders/[siteId]">) {
  const { lang, siteId } = await params;
  if (!isLang(lang)) notFound();
  const site = await getSite(siteId);
  const evidence = await getSiteEvidence(siteId);
  if (!site || !evidence) notFound();
  const t = getDictionary(lang);
  const [actions, groups, meta, standard] = await Promise.all([
    getRecommendedActions(siteId),
    getTaskGroups(),
    getWorkOrderMeta(),
    getTargetStandard(),
  ]);
  const reasons = siteReasons(site, t);

  // Short forwarding text: what / when / report-back. Roles stay blank; no costs.
  const sorted = [...actions].sort((a, b) => a.start.localeCompare(b.start));
  const whatsapp = [
    `${t.orders.orderTitle}: ${pick(site.name, lang)}`,
    t.orders.draft,
    ...sorted.map(
      (a) =>
        `• ${pick(a.dates, lang)}: ${t.ghat.actions.groups[a.taskGroup]} — ${
          a.responsible ? `${a.responsible}${a.responsibleIsAssumption ? ` ${t.common.assumedConfirm}` : ""}` : t.common.assignBlank
        }`,
    ),
    ...(sorted.some((a) => !a.verified) ? [t.common.recommendation] : []),
    fill(t.orders.reportBack, { date: pick(meta.reportBackBy, lang) }),
  ].join("\n");

  return (
    <div className="flex flex-col gap-4">
      <div className="no-print mx-auto flex w-full max-w-[210mm] flex-wrap items-center justify-between gap-3">
        <Link href={`/${lang}/orders/`} className="inline-flex items-center gap-1 text-sm text-slate-600 hover:text-navy hover:underline">
          <ChevronLeft aria-hidden className="h-4 w-4" />
          {t.orders.title}
        </Link>
        <div className="flex flex-wrap gap-2">
          <PrintButton label={t.common.print} />
          <CopyTextButton text={whatsapp} label={t.common.copy} copiedLabel={t.common.copied} failedLabel={t.common.copyFailed} />
        </div>
      </div>

      <WorkOrder
        site={site}
        actions={actions}
        groups={groups}
        meta={meta}
        standard={standard}
        printedNames={evidence.printedNames}
        reasons={reasons}
        lang={lang}
        t={t}
      />

      <details className="no-print mx-auto w-full max-w-[210mm] rounded border border-slate-200 bg-white px-4 py-2 text-xs">
        <summary className="cursor-pointer font-medium text-slate-700">{t.orders.whatsappTitle}</summary>
        <pre className="mt-2 font-sans whitespace-pre-wrap text-slate-800">{whatsapp}</pre>
      </details>
    </div>
  );
}
