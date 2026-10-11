import { Info, Languages } from "lucide-react";
import type { Lang } from "@/lib/data/types";
import type { Dictionary } from "@/lib/i18n";

/** Permanent notice: placeholder data, historical only, pages unverified. Printed too. */
export function DataNoticeBanner({ lang, t }: { lang: Lang; t: Dictionary }) {
  return (
    <div role="note" className="border-b border-slate-300 bg-slate-100">
      <div className="mx-auto flex max-w-7xl flex-col gap-1 px-4 py-2 text-xs text-slate-700 sm:px-6">
        <p className="flex items-start gap-2">
          <Info aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
          <span>
            <strong className="font-semibold text-slate-900">{t.notice.title}.</strong> {t.notice.body} {t.notice.pages}
          </span>
        </p>
        {lang === "hi" && t.notice.hindi && (
          <p className="flex items-start gap-2">
            <Languages aria-hidden className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-500" />
            <span className="font-medium text-slate-900">{t.notice.hindi}</span>
          </p>
        )}
      </div>
    </div>
  );
}
