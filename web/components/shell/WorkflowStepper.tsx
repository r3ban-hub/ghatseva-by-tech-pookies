"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRight } from "lucide-react";
import type { Lang } from "@/lib/data/types";

export interface StepView {
  key: string;
  label: string;
  href: string;
  match: string;
  ready: boolean;
  title?: string;
}

interface Props {
  lang: Lang;
  steps: StepView[];
  label: string;
  plannedLabel: string;
}

/** Rank → Flag → Recommend → Plan → Assign → Estimate → Brief. Highlights the step(s) for the current page. */
export function WorkflowStepper({ lang, steps, label, plannedLabel }: Props) {
  const pathname = usePathname() ?? `/${lang}/`;
  const rest = pathname.replace(new RegExp(`^/${lang}/?`), "");
  const isCurrent = (match: string) => (match === "" ? rest === "" : rest.startsWith(match));

  return (
    <nav aria-label={label} className="no-print border-b border-slate-200 bg-white">
      <ol className="mx-auto flex max-w-7xl items-center gap-1 overflow-x-auto px-4 py-2 text-sm sm:px-6">
        {steps.map((step, i) => {
          const current = isCurrent(step.match);
          return (
            <li key={step.key} className="flex shrink-0 items-center gap-1">
              {i > 0 && <ChevronRight aria-hidden className="h-3.5 w-3.5 text-slate-300" />}
              <Link
                href={step.href}
                title={step.title}
                aria-current={current ? "step" : undefined}
                className={[
                  "inline-flex items-center gap-1.5 rounded px-2 py-1 transition-colors",
                  current
                    ? "bg-navy-soft font-semibold text-navy"
                    : step.ready
                      ? "text-slate-700 hover:bg-slate-100 hover:text-navy"
                      : "text-slate-400 hover:bg-slate-50 hover:text-slate-600",
                ].join(" ")}
              >
                <span
                  aria-hidden
                  className={[
                    "inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold",
                    current ? "bg-navy text-white" : step.ready ? "bg-slate-200 text-slate-700" : "border border-slate-300 text-slate-400",
                  ].join(" ")}
                >
                  {i + 1}
                </span>
                {step.label}
                {!step.ready && <span className="text-[11px] font-normal text-slate-400">({plannedLabel})</span>}
              </Link>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
