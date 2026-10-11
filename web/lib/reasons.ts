import type { SiteRanking } from "@/lib/data/types";
import { fill, type Dictionary } from "@/lib/i18n";
import { FLAG_ORDER } from "@/lib/flags";

/** Plain-words sentences for a site's supplied flags, filled with PRD v2 §6.5 figures. */
export function siteReasons(site: SiteRanking, t: Dictionary): string[] {
  // A ghat can be Tier 2 on DO without carrying a DO flag (e.g. 8 of 18 below 5, lowest 4):
  // lead with that DO result so the tier is explained.
  const hasDoFlag = site.flags.some((f) => f === "DO_SEVERE" || f === "DO_OFTEN_LOW");
  const lead = !hasDoFlag && site.doBelow5.n > 0 ? [fill(t.flagSentence.DO_OFTEN_LOW, { n: site.doBelow5.n, N: site.doBelow5.N })] : [];
  return [...lead, ...FLAG_ORDER.filter((f) => site.flags.includes(f)).map((flag) => {
    switch (flag) {
      case "DO_SEVERE":
        return fill(t.flagSentence.DO_SEVERE, { n: site.doBelow4, N: site.doBelow5.N, min: site.doMin });
      case "DO_ZERO":
        return fill(t.ghat.flagSentence.DO_ZERO, { n: site.doZeroCount });
      case "DO_OFTEN_LOW":
        return fill(t.flagSentence.DO_OFTEN_LOW, { n: site.doBelow5.n, N: site.doBelow5.N });
      case "BOD_OFTEN_HIGH":
        return fill(t.ghat.flagSentence.BOD_OFTEN_HIGH, { n: site.bodAbove3.n, N: site.bodAbove3.N });
      case "PH_OUT":
        return fill(t.ghat.flagSentence.PH_OUT, { n: site.phOutOfRange.n, N: site.phOutOfRange.N });
      case "DATA_GAP":
        return t.ghat.flagSentence.DATA_GAP;
      case "SITE_IDENTITY":
        return t.ghat.flagSentence.SITE_IDENTITY;
    }
  })];
}
