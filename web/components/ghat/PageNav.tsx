interface Props {
  label: string;
  items: { id: string; text: string }[];
}

/** In-page anchors for the long detail page. */
export function PageNav({ label, items }: Props) {
  return (
    <nav aria-label={label} className="no-print -mx-1 flex flex-wrap items-center gap-1 text-sm">
      <span className="px-1 text-xs font-medium text-slate-500">{label}:</span>
      {items.map((it) => (
        <a
          key={it.id}
          href={`#${it.id}`}
          className="rounded border border-slate-200 bg-white px-2 py-0.5 text-slate-700 transition-colors hover:border-navy-line hover:bg-navy-soft hover:text-navy"
        >
          {it.text}
        </a>
      ))}
    </nav>
  );
}
