import Link from "next/link";
import { Construction } from "lucide-react";
import type { Lang } from "@/lib/data/types";
import { fill, type Dictionary } from "@/lib/i18n";
import { screenHref } from "@/lib/screens";

type PlannedKey = keyof Dictionary["planned"]["screens"];

/** Placeholder for screens scheduled for later stages, so navigation never dead-ends. */
export function PlannedScreen({ lang, t, screen, context }: { lang: Lang; t: Dictionary; screen: PlannedKey; context?: string }) {
  return (
    <div className="hatch mx-auto max-w-2xl rounded-md border border-dashed border-slate-400 bg-white px-6 py-10 text-center">
      <Construction aria-hidden className="mx-auto h-6 w-6 text-slate-500" />
      <h1 className="mt-3 text-lg font-semibold text-slate-900">
        {fill(t.planned.title, { screen: t.planned.screens[screen] })}
      </h1>
      {context && <p className="mt-1 text-sm font-medium text-slate-700">{context}</p>}
      <p className="mt-2 text-sm text-slate-600">{t.planned.body}</p>
      <Link
        href={screenHref(lang, "overview")}
        className="mt-5 inline-flex rounded border border-navy bg-navy px-3 py-1.5 text-sm font-medium text-white hover:bg-navy-strong"
      >
        {t.planned.back}
      </Link>
    </div>
  );
}
