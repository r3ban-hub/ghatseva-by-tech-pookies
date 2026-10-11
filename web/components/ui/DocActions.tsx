"use client";

import { useState } from "react";
import { Copy, Download, Printer } from "lucide-react";

const BTN =
  "inline-flex items-center gap-1.5 rounded border border-slate-300 bg-white px-2.5 py-1 text-sm text-slate-800 transition-colors hover:border-navy hover:text-navy";

export function PrintButton({ label }: { label: string }) {
  return (
    <button type="button" onClick={() => window.print()} className={BTN}>
      <Printer aria-hidden className="h-4 w-4" />
      {label}
    </button>
  );
}

export function CopyTextButton({ text, label, copiedLabel, failedLabel }: { text: string; label: string; copiedLabel: string; failedLabel: string }) {
  const [state, setState] = useState<"idle" | "copied" | "failed">("idle");
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      setState("failed");
    }
    setTimeout(() => setState("idle"), 2000);
  };
  return (
    <button type="button" onClick={copy} className={BTN} aria-live="polite">
      <Copy aria-hidden className="h-4 w-4" />
      {state === "copied" ? copiedLabel : state === "failed" ? failedLabel : label}
    </button>
  );
}

export function DownloadTextButton({ text, filename, label }: { text: string; filename: string; label: string }) {
  const download = () => {
    const url = URL.createObjectURL(new Blob([text], { type: "text/markdown;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    // Attach before clicking and revoke later; some browsers cancel the download otherwise.
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  return (
    <button type="button" onClick={download} className={BTN}>
      <Download aria-hidden className="h-4 w-4" />
      {label}
    </button>
  );
}
