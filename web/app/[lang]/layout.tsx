import { notFound } from "next/navigation";
import { AppHeader } from "@/components/shell/AppHeader";
import { DataNoticeBanner } from "@/components/shell/DataNoticeBanner";
import { SiteFooter } from "@/components/shell/SiteFooter";
import { WorkflowStepper, type StepView } from "@/components/shell/WorkflowStepper";
import { LANGS, getDictionary, isLang } from "@/lib/i18n";
import { SCREEN_READY, workflowSteps } from "@/lib/screens";

export const dynamicParams = false;

export function generateStaticParams() {
  return LANGS.map((lang) => ({ lang }));
}

export default async function LangLayout({ children, params }: LayoutProps<"/[lang]">) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const t = getDictionary(lang);

  const steps: StepView[] = workflowSteps(lang).map((s) => ({
    key: s.key,
    label: t.nav.steps[s.key],
    href: s.href,
    match: s.match,
    ready: SCREEN_READY[s.screen],
    title: s.key === "recommend" ? t.nav.recommendHint : undefined,
  }));

  return (
    // `lang` on the wrapper so screen readers and fonts switch for Hindi pages.
    <div lang={lang} className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only z-50 rounded bg-white px-3 py-2 text-sm font-medium text-navy focus:not-sr-only focus:absolute focus:top-2 focus:left-2"
      >
        {t.nav.skip}
      </a>
      <AppHeader lang={lang} t={t} />
      <DataNoticeBanner lang={lang} t={t} />
      <WorkflowStepper lang={lang} steps={steps} label={t.nav.workflow} plannedLabel={t.nav.planned} />
      <main id="main" className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6">
        {children}
      </main>
      <SiteFooter t={t} />
    </div>
  );
}
