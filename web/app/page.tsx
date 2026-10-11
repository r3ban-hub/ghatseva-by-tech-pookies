import { RootRedirect } from "@/components/shell/RootRedirect";

// Static export has no server redirects, so "/" offers both languages and
// forwards to English in the browser.
export default function RootPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 px-6">
      <RootRedirect target="en/" />
      <div>
        <p className="text-sm font-semibold tracking-wide text-navy uppercase">Visarjan Ghat Watch</p>
        <h1 className="mt-1 text-xl font-semibold text-slate-900">
          Choose a language <span lang="hi">· भाषा चुनें</span>
        </h1>
      </div>
      <div className="flex gap-3">
        <a
          href="en/"
          className="rounded border border-navy bg-navy px-4 py-2 text-sm font-medium text-white hover:bg-navy-strong"
        >
          English
        </a>
        <a
          href="hi/"
          lang="hi"
          className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800 hover:border-navy"
        >
          हिंदी
        </a>
      </div>
    </main>
  );
}
