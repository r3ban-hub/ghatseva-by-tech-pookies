import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 px-6">
      <p className="text-sm font-semibold tracking-wide text-navy uppercase">Visarjan Ghat Watch</p>
      <h1 className="text-xl font-semibold text-slate-900">Page not found</h1>
      <p className="text-sm text-slate-600">
        This address does not exist in Visarjan Ghat Watch.{" "}
        <span lang="hi">यह पता विसर्जन घाट वॉच में मौजूद नहीं है।</span>
      </p>
      <div className="flex gap-3 text-sm">
        <Link href="/en/" className="font-medium text-accent underline underline-offset-2">
          English overview
        </Link>
        <Link href="/hi/" lang="hi" className="font-medium text-accent underline underline-offset-2">
          हिंदी सारांश
        </Link>
      </div>
    </main>
  );
}
