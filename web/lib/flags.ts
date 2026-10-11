import type { FlagCode, FlagSeverity } from "@/lib/data/types";

/** Display severity per PRD v2 §6.3. Presentation only; which flags a ghat has comes from the data. */
export const FLAG_SEVERITY: Record<FlagCode, FlagSeverity> = {
  DO_SEVERE: "red",
  DO_ZERO: "red",
  DO_OFTEN_LOW: "amber",
  BOD_OFTEN_HIGH: "amber",
  PH_OUT: "amber",
  DATA_GAP: "neutral",
  SITE_IDENTITY: "neutral",
};

export const FLAG_ORDER: FlagCode[] = [
  "DO_SEVERE",
  "DO_ZERO",
  "DO_OFTEN_LOW",
  "BOD_OFTEN_HIGH",
  "PH_OUT",
  "DATA_GAP",
  "SITE_IDENTITY",
];
