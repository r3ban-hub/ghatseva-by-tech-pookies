import type { FlagCode, Lang, SiteNote } from "@/lib/data/types";
import { fill, pick, type Dictionary } from "@/lib/i18n";
import { ProvenanceTag } from "@/components/data/ProvenanceTag";
import { SourceRefLink } from "@/components/data/SourceRefLink";

/**
 * Notes supplied with a site, each with its provenance and page references.
 * `refsOnly`: flags whose sentence is already shown nearby; only their page references are listed.
 * `provenanceTag`: false when the surrounding item already shows the provenance tag.
 */
export function SiteNoteList({
  notes,
  lang,
  t,
  refsOnly = [],
  provenanceTag = true,
}: {
  notes: SiteNote[];
  lang: Lang;
  t: Dictionary;
  refsOnly?: FlagCode[];
  provenanceTag?: boolean;
}) {
  // A refs-only note with no page references and no tag would render as an empty row.
  const shown = notes.filter((n) => !(refsOnly.includes(n.flag) && n.refs.length === 0 && !provenanceTag));
  if (shown.length === 0) return null;
  return (
    <ul className="mt-1.5 space-y-1.5">
      {shown.map((note, i) => (
        <li key={i} className="text-xs text-slate-700">
          {!refsOnly.includes(note.flag) && <p>{pick(note.text, lang)}</p>}
          <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
            {provenanceTag && (
              <ProvenanceTag
                provenance={note.provenance}
                label={t.provenance[note.provenance]}
                title={note.provenance === "backend" ? t.provenance.backendLong : t.provenance.prdLong}
              />
            )}
            {note.refs.map((r) => (
              <SourceRefLink
                key={`${r.year}-${r.page}`}
                source={r}
                text={fill(t.source.report, { year: r.year, page: r.page })}
                statusText={r.verified ? t.source.verified : t.source.unverified}
              />
            ))}
          </p>
        </li>
      ))}
    </ul>
  );
}
