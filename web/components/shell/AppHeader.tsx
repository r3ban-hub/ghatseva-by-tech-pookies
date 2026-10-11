import Link from "next/link";
import { BookOpen } from "lucide-react";
import type { Lang } from "@/lib/data/types";
import type { Dictionary } from "@/lib/i18n";
import { screenHref } from "@/lib/screens";
import { LanguageToggle } from "./LanguageToggle";

export function AppHeader({ lang, t }: { lang: Lang; t: Dictionary }) {
  return (
    <header className="bg-navy text-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
        <div className="min-w-0">
          <Link href={screenHref(lang, "overview")} className="group inline-flex items-baseline gap-2">
            <span aria-hidden className="inline-block h-3 w-3 translate-y-px rounded-sm border-2 border-white/80 bg-accent" />
            <span className="text-base font-semibold tracking-tight group-hover:underline">{t.product.name}</span>
          </Link>
          <p className="mt-0.5 text-xs text-white/75">
            {t.product.tagline} · <span className="font-medium text-white">{t.product.visarjan}</span>
          </p>
        </div>
        <div className="no-print flex items-center gap-3">
          <Link
            href={screenHref(lang, "method")}
            className="inline-flex items-center gap-1.5 rounded px-2 py-1 text-sm text-white/85 transition-colors hover:bg-white/10 hover:text-white"
          >
            <BookOpen aria-hidden className="h-4 w-4" />
            {t.nav.method}
          </Link>
          <LanguageToggle lang={lang} label={t.nav.language} names={{ en: "English", hi: "हिंदी" }} />
        </div>
      </div>
    </header>
  );
}
