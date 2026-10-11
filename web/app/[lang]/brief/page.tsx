import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getHeadlines, getMeta, getRanking, getRecommendedActions, getTargetStandard } from "@/lib/data";
import type { RecommendedAction } from "@/lib/data/types";
import { fill, getDictionary, isLang, pick } from "@/lib/i18n";
import { siteReasons } from "@/lib/reasons";
import { TierBadge } from "@/components/data/TierBadge";
import { DownloadTextButton, PrintButton } from "@/components/ui/DocActions";

export async function generateMetadata({ params }: PageProps<"/[lang]/brief">): Promise<Metadata> {
  const { lang } = await params;
  return isLang(lang) ? { title: getDictionary(lang).brief.title } : {};
}

export default async function BriefPage({ params }: PageProps<"/[lang]/brief">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const t = getDictionary(lang);
  const b = t.brief;
  const [meta, sites, headlines, standard] = await Promise.all([getMeta(), getRanking(), getHeadlines(), getTargetStandard()]);

  // Group PRD actions by action, listing the ghats each applies to (ghats in rank order).
  const byAction = new Map<string, { action: RecommendedAction; ghats: string[] }>();
  for (const s of sites) {
    for (const a of await getRecommendedActions(s.siteId)) {
      const entry = byAction.get(a.id) ?? { action: a, ghats: [] };
      entry.ghats.push(pick(s.name, lang));
      byAction.set(a.id, entry);
    }
  }
  const actions = [...byAction.values()].sort((x, y) => x.action.start.localeCompare(y.action.start));

  const findingText = (h: (typeof headlines)[number]) =>
    `${pick(h.label, lang)}: ${
      h.value.kind === "fraction" ? fill(t.overview.headlines.ofReadings, { n: h.value.value.n, N: h.value.value.N }) : h.value.value
    }${h.detail ? ` (${pick(h.detail, lang)})` : ""}`;

  const limits = [pick(meta.coverage.absentDetail, lang), ...t.method.limitItems];

  const md = [
    `# ${b.title}`,
    "",
    `> ${t.notice.title}. ${t.notice.body}${lang === "hi" ? ` ${t.notice.hindi}` : ""}`,
    "",
    `## ${b.scope}`,
    b.scopeBody,
    "",
    `## ${b.findings}`,
    ...headlines.map((h) => `- ${findingText(h)}`),
    "",
    `## ${b.priorities}`,
    `| ${b.col.rank} | ${b.col.ghat} | ${b.col.tier} | ${b.col.concern} |`,
    "|---|---|---|---|",
    ...sites.map(
      (s) =>
        `| ${s.rank} | ${pick(s.name, lang)} | ${fill(t.tier.label, { n: s.tier })}${s.highRisk ? ` · ${t.overview.ranking.highRisk}` : ""} | ${siteReasons(s, t)[0] ?? ""} |`,
    ),
    "",
    `## ${b.actions}`,
    b.actionsBody,
    ...actions.map(
      ({ action, ghats }) =>
        `- **${pick(action.dates, lang)} · ${t.ghat.actions.groups[action.taskGroup]}:** ${pick(action.text, lang)} — ${ghats.length === sites.length ? t.common.allGhats : ghats.join(", ")} (${t.common.recommendation})`,
    ),
    "",
    `## ${b.target}`,
    ...standard.items.map((i) => `- [ ] ${pick(i.parameter, lang)}: ${pick(i.target, lang)}${i.inCurrentData ? "" : ` (${t.ghat.target.notInData})`}`),
    pick(standard.interimNote, lang),
    "",
    `## ${b.resources}`,
    b.resourcesBody,
    "",
    `## ${b.gaps}`,
    ...limits.map((l) => `- ${l}`),
    "",
    `_${b.generated}_`,
  ].join("\n");

  const h2 = "mt-5 text-base font-semibold text-slate-900";

  return (
    <div className="flex flex-col gap-4">
      <div className="no-print mx-auto flex w-full max-w-[210mm] flex-wrap items-center justify-between gap-3">
        <Link href={`/${lang === "en" ? "hi" : "en"}/brief/`} className="text-sm text-accent underline-offset-2 hover:underline">
          {b.otherLang}
        </Link>
        <div className="flex flex-wrap gap-2">
          <PrintButton label={t.common.print} />
          <DownloadTextButton text={md} filename={`visarjan-ghat-brief-${lang}.md`} label={t.common.download} />
        </div>
      </div>

      <article className="mx-auto w-full max-w-[210mm] rounded-md border border-slate-300 bg-white px-4 py-5 text-sm text-slate-800 shadow-sm sm:px-7 sm:py-6 print:max-w-none print:border-0 print:p-0 print:shadow-none">
        <h1 className="text-xl font-semibold text-slate-900">{b.title}</h1>
        <p className="mt-1 text-xs text-slate-600">{b.intro}</p>
        {lang === "hi" && <p className="mt-1 text-xs font-semibold text-slate-900">{t.notice.hindi}</p>}

        <h2 className={h2}>{b.scope}</h2>
        <p className="mt-1">{b.scopeBody}</p>

        <h2 className={h2}>{b.findings}</h2>
        <ul className="mt-1 list-disc space-y-0.5 pl-5">
          {headlines.map((h) => (
            <li key={h.id} className={h.emphasis === "caveat" ? "font-medium" : ""}>
              {findingText(h)}
            </li>
          ))}
        </ul>

        <h2 className={h2}>{b.priorities}</h2>
        <table className="mt-1 w-full border-collapse text-xs">
          <thead className="text-left text-slate-600">
            <tr className="border-b border-slate-300">
              <th scope="col" className="py-1 pr-2">{b.col.rank}</th>
              <th scope="col" className="py-1 pr-2">{b.col.ghat}</th>
              <th scope="col" className="py-1 pr-2">{b.col.tier}</th>
              <th scope="col" className="py-1">{b.col.concern}</th>
            </tr>
          </thead>
          <tbody>
            {sites.map((s) => (
              <tr key={s.siteId} className="print-break-avoid border-b border-slate-200 align-top">
                <td className="py-1.5 pr-2 font-semibold tabular-nums">{s.rank}</td>
                <td className="py-1.5 pr-2 font-medium text-slate-900">{pick(s.name, lang)}</td>
                <td className="py-1.5 pr-3">
                  <TierBadge tier={s.tier} label={fill(t.tier.label, { n: s.tier })} />
                  {s.highRisk && (
                    <span className="mt-1 block text-[11px] font-semibold tracking-wide whitespace-nowrap text-risk-red uppercase">
                      {t.overview.ranking.highRisk}
                    </span>
                  )}
                </td>
                <td className="py-1.5">{siteReasons(s, t)[0]}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h2 className={h2}>{b.actions}</h2>
        <p className="mt-1 text-xs text-slate-600">{b.actionsBody}</p>
        <ul className="mt-1.5 space-y-2">
          {actions.map(({ action, ghats }) => (
            <li key={action.id} className="print-break-avoid">
              <span className="font-semibold text-slate-900">
                {pick(action.dates, lang)} · {t.ghat.actions.groups[action.taskGroup]}:
              </span>{" "}
              {pick(action.text, lang)}
              <span className="mt-0.5 block text-xs text-slate-600">
                {ghats.length === sites.length ? t.common.allGhats : ghats.join(", ")}{" "}
                <span className="text-slate-500 italic">({t.common.recommendation})</span>
              </span>
            </li>
          ))}
        </ul>

        <h2 className={h2}>{b.target}</h2>
        <ul className="mt-1 space-y-0.5">
          {standard.items.map((i) => (
            <li key={i.id}>
              ☐ <span className="font-medium">{pick(i.parameter, lang)}</span>: {pick(i.target, lang)}
              {!i.inCurrentData && <span className="text-slate-500"> ({t.ghat.target.notInData})</span>}
            </li>
          ))}
        </ul>
        <p className="mt-1 text-xs text-slate-700">{pick(standard.interimNote, lang)}</p>

        <h2 className={h2}>{b.resources}</h2>
        <p className="mt-1">{b.resourcesBody}</p>

        <h2 className={h2}>{b.gaps}</h2>
        <ul className="mt-1 list-disc space-y-0.5 pl-5">
          {limits.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>

        <p className="mt-5 border-t border-slate-300 pt-2 text-[11px] text-slate-600">{b.generated}</p>
      </article>
    </div>
  );
}
