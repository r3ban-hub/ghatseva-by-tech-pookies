import { FileText } from "lucide-react";
import type { SourceRef } from "@/lib/data/types";

interface Props {
  source: SourceRef;
  text: string;
  statusText: string;
  /** Put the check status on its own line (narrow table cells). */
  stacked?: boolean;
}

/** "2023 report, p.60 · page unverified". The PDF filename is in the tooltip. */
export function SourceRefLink({ source, text, statusText, stacked = false }: Props) {
  return (
    <span
      title={`${source.pdf}, PDF page ${source.page}`}
      className={`inline-flex items-center gap-x-1 text-xs text-slate-600 ${stacked ? "flex-wrap" : "whitespace-nowrap"}`}
    >
      <FileText aria-hidden className="h-3 w-3 text-slate-400" />
      <span className="font-medium whitespace-nowrap text-slate-700">{text}</span>
      <span className={`${source.verified ? "text-accent" : "text-slate-500 italic"} ${stacked ? "basis-full pl-4" : ""}`}>
        {stacked ? statusText : `· ${statusText}`}
      </span>
    </span>
  );
}
