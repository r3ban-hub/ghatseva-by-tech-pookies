"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Lang } from "@/lib/data/types";

interface Props {
  lang: Lang;
  label: string;
  names: Record<Lang, string>;
}

/** Switches the `/en/` or `/hi/` prefix of the current path. Both versions are prebuilt. */
export function LanguageToggle({ lang, label, names }: Props) {
  const pathname = usePathname() ?? `/${lang}/`;
  const hrefFor = (target: Lang) => {
    const swapped = pathname.replace(/^\/(en|hi)(?=\/|$)/, `/${target}`);
    return swapped.endsWith("/") ? swapped : `${swapped}/`;
  };

  return (
    <nav aria-label={label} className="flex items-center rounded border border-white/25 p-0.5 text-sm">
      {(["en", "hi"] as const).map((target) => {
        const active = target === lang;
        return (
          <Link
            key={target}
            href={hrefFor(target)}
            lang={target}
            hrefLang={target}
            aria-current={active ? "true" : undefined}
            className={
              active
                ? "rounded-sm bg-white px-2.5 py-1 font-medium text-navy"
                : "rounded-sm px-2.5 py-1 text-white/85 transition-colors hover:bg-white/10 hover:text-white"
            }
          >
            {names[target]}
          </Link>
        );
      })}
    </nav>
  );
}
