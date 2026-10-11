import { FileText } from "lucide-react";
import type { SourceRef } from "@/lib/data/types";

interface Props {
  source: SourceRef;
  text: string;
  statusText: string;
}

/** "2023 report, p.60 · page unverified". The PDF filename is in the tooltip. */
export function SourceRefLink({ source, text, statusText }: Props) {
  return (
    <span
      title={`${source.pdf}, PDF page ${source.page}`}
      className="inline-flex items-center gap-1 text-xs whitespace-nowrap text-slate-600"
    >
      <FileText aria-hidden className="h-3 w-3 text-slate-400" />
      <span className="font-medium text-slate-700">{text}</span>
      <span className={source.verified ? "text-accent" : "text-slate-500 italic"}>· {statusText}</span>
    </span>
  );
}
