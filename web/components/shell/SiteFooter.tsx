import type { Dictionary } from "@/lib/i18n";

export function SiteFooter({ t }: { t: Dictionary }) {
  return (
    <footer className="mt-auto border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-1.5 px-4 py-5 text-xs text-slate-600 sm:px-6">
        <p className="font-medium text-slate-800">{t.footer.disclaimer}</p>
        <p>{t.footer.sources}</p>
        <p className="text-slate-500">{t.footer.build}</p>
      </div>
    </footer>
  );
}
