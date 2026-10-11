export interface DotPoint {
  slot: number;
  value: number;
  title: string;
}

export interface MissingMark {
  slot: number;
  short: string;
  title: string;
}

export interface CriterionLine {
  value: number;
  label: string;
  kind: "standard" | "severity";
}

interface Props {
  id: string;
  title: string;
  description: string;
  unitLabel: string;
  seasonLabels: string[];
  phaseLabels: string[];
  points: DotPoint[];
  missing: MissingMark[];
  criteria: CriterionLine[];
  domain: [number, number];
  missingLabel: string;
}

const W = 720;
const H = 260;
const M = { top: 14, right: 118, bottom: 70, left: 46 };
const PLOT_W = W - M.left - M.right;
const PLOT_H = H - M.top - M.bottom;

function niceStep(range: number): number {
  const raw = range / 5;
  for (const s of [0.25, 0.5, 1, 2, 4, 5, 10, 20]) if (s >= raw) return s;
  return 50;
}

/**
 * One dot per reading, positioned by season and phase. Dots are deliberately not joined.
 * Criterion lines come from the supplied CPCB criteria; missing cells sit in a strip below the axis.
 */
export function DotPlot({ id, title, description, unitLabel, seasonLabels, phaseLabels, points, missing, criteria, domain, missingLabel }: Props) {
  const slots = seasonLabels.length * phaseLabels.length;
  const slotW = PLOT_W / slots;
  const [min, max] = domain;
  const x = (slot: number) => M.left + slotW * (slot + 0.5);
  const y = (v: number) => M.top + PLOT_H - ((v - min) / (max - min)) * PLOT_H;
  const step = niceStep(max - min);
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) ticks.push(Number(v.toFixed(2)));
  const base = M.top + PLOT_H;
  const hatchId = `${id}-hatch`;

  return (
    <figure className="print-break-avoid">
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-labelledby={`${id}-title ${id}-desc`}
          className="h-auto w-full min-w-[560px] text-[10px]"
        >
          <title id={`${id}-title`}>{title}</title>
          <desc id={`${id}-desc`}>{description}</desc>
          <defs>
            <pattern id={hatchId} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="5" stroke="#94a3b8" strokeWidth="1.5" />
            </pattern>
          </defs>

          {/* Alternate season bands */}
          {seasonLabels.map((_, i) =>
            i % 2 === 1 ? (
              <rect key={i} x={M.left + i * 3 * slotW} y={M.top} width={3 * slotW} height={PLOT_H} className="fill-slate-50" />
            ) : null,
          )}

          {/* Y grid and ticks */}
          {ticks.map((v) => (
            <g key={v}>
              <line x1={M.left} x2={M.left + PLOT_W} y1={y(v)} y2={y(v)} className="stroke-slate-200" strokeWidth="1" />
              <text x={M.left - 6} y={y(v)} dy="0.32em" textAnchor="end" className="fill-slate-500 tabular-nums">
                {v}
              </text>
            </g>
          ))}
          <text
            transform={`translate(12 ${M.top + PLOT_H / 2}) rotate(-90)`}
            textAnchor="middle"
            className="fill-slate-600 font-medium"
          >
            {unitLabel}
          </text>

          {/* Axes */}
          <line x1={M.left} x2={M.left} y1={M.top} y2={base} className="stroke-slate-400" />
          <line x1={M.left} x2={M.left + PLOT_W} y1={base} y2={base} className="stroke-slate-400" />

          {/* Criterion lines */}
          {criteria.map((c) => (
            <g key={`${c.kind}-${c.value}`}>
              <line
                x1={M.left}
                x2={M.left + PLOT_W}
                y1={y(c.value)}
                y2={y(c.value)}
                stroke={c.kind === "standard" ? "#0f2a44" : "#64748b"}
                strokeWidth={c.kind === "standard" ? 1.5 : 1.25}
                strokeDasharray={c.kind === "standard" ? "6 4" : "2 3"}
              />
              <text x={M.left + PLOT_W + 6} y={y(c.value)} dy="0.32em" className={c.kind === "standard" ? "fill-navy font-semibold" : "fill-slate-500"}>
                {c.label}
              </text>
            </g>
          ))}

          {/* Phase and season labels */}
          {seasonLabels.map((label, si) => (
            <g key={label}>
              {phaseLabels.map((p, pi) => (
                <text key={p} x={x(si * 3 + pi)} y={base + 13} textAnchor="middle" className="fill-slate-500 text-[8.5px]">
                  {p}
                </text>
              ))}
              <text x={M.left + (si * 3 + 1.5) * slotW} y={base + 28} textAnchor="middle" className="fill-slate-700 font-medium">
                {label}
              </text>
              {si > 0 && (
                <line x1={M.left + si * 3 * slotW} x2={M.left + si * 3 * slotW} y1={base} y2={base + 32} className="stroke-slate-200" />
              )}
            </g>
          ))}

          {/* Missing strip */}
          <text x={M.left - 6} y={base + 48} dy="0.32em" textAnchor="end" className="fill-slate-500">
            {missingLabel}
          </text>
          {missing.map((m) => (
            <g key={m.slot}>
              <title>{m.title}</title>
              <rect x={x(m.slot) - 9} y={base + 41} width="18" height="14" rx="2" fill={`url(#${hatchId})`} className="stroke-slate-400" strokeDasharray="2 1.5" />
              <text x={x(m.slot)} y={base + 48} dy="0.32em" textAnchor="middle" className="fill-slate-700 text-[7.5px] font-semibold">
                {m.short}
              </text>
            </g>
          ))}

          {/* Readings */}
          {points.map((p) => (
            <g key={p.slot}>
              <title>{p.title}</title>
              <circle cx={x(p.slot)} cy={y(p.value)} r="5" className="fill-navy stroke-white" strokeWidth="1.5" />
            </g>
          ))}
        </svg>
      </div>
    </figure>
  );
}
