import type { Provenance } from "@/lib/data/types";

const STYLES: Record<Provenance, string> = {
  backend: "border-navy bg-white text-navy font-medium",
  prd: "border-navy-line bg-navy-soft text-navy",
  blank: "border-dashed border-slate-300 bg-white text-slate-500",
};

interface Props {
  provenance: Provenance;
  label: string;
  title?: string;
  /** Extra reference shown after the label, e.g. "§6.5". */
  detail?: string;
}

/** Small label telling the reader where a figure comes from. */
export function ProvenanceTag({ provenance, label, title, detail }: Props) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 rounded-sm border px-1.5 py-px text-[10.5px] leading-4 whitespace-nowrap ${STYLES[provenance]}`}
    >
      {label}
      {detail && <span className="opacity-75">· {detail}</span>}
    </span>
  );
}
