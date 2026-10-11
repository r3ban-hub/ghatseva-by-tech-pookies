import type { Lang } from "@/lib/data/types";

export type ScreenKey = "overview" | "ghat" | "plan" | "orders" | "estimate" | "brief" | "method";

/** Which screens are built. Flip to true as each stage lands. */
export const SCREEN_READY: Record<ScreenKey, boolean> = {
  overview: true,
  ghat: true,
  plan: true,
  orders: true,
  estimate: true,
  brief: true,
  method: true,
};

const PATHS: Record<ScreenKey, string> = {
  overview: "",
  ghat: "ghats/",
  plan: "plan/",
  orders: "orders/",
  estimate: "estimate/",
  brief: "brief/",
  method: "method/",
};

export function screenHref(lang: Lang, screen: ScreenKey, suffix = ""): string {
  return `/${lang}/${PATHS[screen]}${suffix}`;
}

export function ghatHref(lang: Lang, siteId: string): string {
  return `/${lang}/ghats/${siteId}/`;
}

export type StepKey = "rank" | "flag" | "recommend" | "plan" | "assign" | "estimate" | "brief";

export interface WorkflowStep {
  key: StepKey;
  screen: ScreenKey;
  href: string;
  /** Path prefix (after /lang/) that marks this step as current. */
  match: string;
}

export function workflowSteps(lang: Lang): WorkflowStep[] {
  return [
    { key: "rank", screen: "overview", href: screenHref(lang, "overview", "#ranking"), match: "" },
    { key: "flag", screen: "overview", href: screenHref(lang, "overview", "#flags"), match: "" },
    { key: "recommend", screen: "ghat", href: screenHref(lang, "overview", "#ranking"), match: "ghats/" },
    { key: "plan", screen: "plan", href: screenHref(lang, "plan"), match: "plan/" },
    { key: "assign", screen: "orders", href: screenHref(lang, "orders"), match: "orders/" },
    { key: "estimate", screen: "estimate", href: screenHref(lang, "estimate"), match: "estimate/" },
    { key: "brief", screen: "brief", href: screenHref(lang, "brief"), match: "brief/" },
  ];
}
