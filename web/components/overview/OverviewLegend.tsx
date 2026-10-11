import type { Provenance, Tier } from "@/lib/data/types";
import { fill, type Dictionary } from "@/lib/i18n";
import { FLAG_ORDER, FLAG_SEVERITY } from "@/lib/flags";
import { TierBadge } from "@/components/data/TierBadge";
import { FlagChip } from "@/components/data/FlagChip";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";

const TIERS: Tier[] = [1, 2, 3, 4];
const PROVENANCES: Provenance[] = ["backend", "prd", "blank"];

export function OverviewLegend({ t }: { t: Dictionary }) {
  const l = t.overview.legend;
  const longText: Record<Provenance, string> = {
    backend: t.provenance.backendLong,
    prd: t.provenance.prdLong,
    blank: t.provenance.blankLong,
  };

  return (
    <details open className="print-break-avoid rounded-md border border-slate-200 bg-white">
      <summary className="cursor-pointer px-4 py-3 text-base font-semibold text-slate-900 select-none">{l.title}</summary>
      <div className="grid gap-6 border-t border-slate-200 px-4 py-4 md:grid-cols-3">
        <div>
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">{l.tiers}</h3>
          <ul className="space-y-2">
            {TIERS.map((tier) => (
              <li key={tier} className="flex items-start gap-2 text-xs text-slate-700">
                <TierBadge tier={tier} label={fill(t.tier.label, { n: tier })} />
                <span>{t.tier[tier]}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">{l.flags}</h3>
          <ul className="space-y-2">
            {FLAG_ORDER.map((code) => (
              <li key={code} className="flex items-start gap-2 text-xs text-slate-700">
                <FlagChip severity={FLAG_SEVERITY[code]} label={t.flag[code].short} identity={code === "SITE_IDENTITY"} />
                <span>{t.flag[code].long}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-xs font-semibold tracking-wide text-slate-500 uppercase">{t.provenance.legendTitle}</h3>
          <ul className="space-y-2">
            {PROVENANCES.map((p) => (
              <li key={p} className="flex items-start gap-2 text-xs text-slate-700">
                <ProvenanceTag provenance={p} label={t.provenance[p]} />
                <span>{longText[p]}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </details>
  );
}
