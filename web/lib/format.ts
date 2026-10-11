import type { Season, SourceRef } from "@/lib/data/types";
import { fill, type Dictionary } from "@/lib/i18n";

export function seasonLabel(season: Season, t: Dictionary): string {
  return fill(t.season, { festival: t.festival[season.festival], year: season.year });
}

export function refText(source: SourceRef, t: Dictionary): string {
  return fill(t.source.report, { year: source.year, page: source.page });
}

export function refStatus(source: SourceRef, t: Dictionary): string {
  return source.verified ? t.source.verified : t.source.unverified;
}

export function paramName(parameter: string, t: Dictionary): string {
  return t.parameterName[parameter] ?? parameter;
}

const METALS = new Set(["Chromium", "Lead", "Zinc", "Copper"]);

/** The supplied CPCB criterion text for a parameter (display only; nothing is compared). */
export function criterionText(parameter: string, t: Dictionary): string {
  const c = t.ghat.criterion;
  if (parameter === "Dissolved oxygen") return c.do;
  if (parameter === "BOD") return c.bod;
  if (parameter === "pH") return c.ph;
  if (parameter === "Conductivity") return c.conductivity;
  if (METALS.has(parameter)) return c.metal;
  return c.none;
}
