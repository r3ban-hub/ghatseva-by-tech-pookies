import type { Lang, Localized } from "@/lib/data/types";
import { en, type Dictionary } from "./en";
import { hi } from "./hi";

export const LANGS: readonly Lang[] = ["en", "hi"];

const dictionaries: Record<Lang, Dictionary> = { en, hi };

export function isLang(value: string): value is Lang {
  return (LANGS as readonly string[]).includes(value);
}

export function getDictionary(lang: Lang): Dictionary {
  return dictionaries[lang];
}

/** Pick the string for the current language. */
export function pick(text: Localized, lang: Lang): string {
  return text[lang];
}

/** Fill `{name}` placeholders. Values are inserted as given; nothing is computed. */
export function fill(template: string, vars: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in vars ? String(vars[key]) : match,
  );
}

export type { Dictionary };
