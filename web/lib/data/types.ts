// Data contract used by every screen. Screens only read these shapes through
// `lib/data/index.ts`, which maps the backend export (lib/data/backend.ts).

export type Lang = "en" | "hi";

export interface Localized {
  en: string;
  hi: string;
}

/**
 * Where a figure comes from. Shown to the user next to the figure.
 * - backend:   computed by the Python backend (ghatwatch) and exported to lib/data/generated/backend.json
 * - prd:       a rule or plan-window description from the team's PRD v2 (text, not data)
 * - blank:     intentionally empty (unassigned role, rate not set)
 */
export type Provenance = "backend" | "prd" | "blank";

export type ReportYear = 2023 | 2024 | 2025;

/**
 * A page in an MPPCB visarjan report. `verified` is true only when every reading this reference
 * cites on that page was matched in the partial manual PDF spot check (verification/pdf_spot_checks.csv).
 */
export interface SourceRef {
  year: ReportYear;
  page: number;
  pdf: string;
  verified: boolean;
  label?: Localized;
}

export interface Fraction {
  n: number;
  N: number;
}

export type Tier = 1 | 2 | 3 | 4;

export type FlagCode =
  | "DO_SEVERE"
  | "DO_ZERO"
  | "DO_OFTEN_LOW"
  | "BOD_OFTEN_HIGH"
  | "PH_OUT"
  | "DATA_GAP"
  | "SITE_IDENTITY";

export type FlagSeverity = "red" | "amber" | "neutral";

export interface SiteNote {
  /** Which flag this note explains. */
  flag: FlagCode;
  text: Localized;
  refs: SourceRef[];
  provenance: Provenance;
}

/** One ghat's row in the PRD v2 §6.5 ranking. All values are supplied, never computed in the UI. */
export interface SiteRanking {
  siteId: string;
  name: Localized;
  /** Standard site name exactly as in the track CSV `site` column. */
  csvSiteName: string;
  waterBody: Localized;
  identityConfidence: "high" | "medium";
  rank: number;
  tier: Tier;
  highRisk: boolean;
  /** Numeric DO readings below 5 mg/l, over numeric DO readings. */
  doBelow5: Fraction;
  /** Numeric DO readings below 4 mg/l (Class D severity line). */
  doBelow4: number;
  /** Lowest numeric DO, as written in the PRD (keeps printed precision). */
  doMin: string;
  doZeroCount: number;
  /** Numeric BOD readings above 3 mg/l, over numeric BOD readings. */
  bodAbove3: Fraction;
  /** Numeric pH readings outside 6.5–8.5, over numeric pH readings. */
  phOutOfRange: Fraction;
  /** Expected cells per parameter: 3 years × 2 festivals × 3 phases. */
  expectedPerParameter: number;
  flags: FlagCode[];
  notes: SiteNote[];
  provenance: Provenance;
  prdRef: string;
}

export type HeadlineValue = { kind: "fraction"; value: Fraction } | { kind: "count"; value: number };

export interface HeadlineFinding {
  id: string;
  label: Localized;
  value: HeadlineValue;
  detail?: Localized;
  refs?: SourceRef[];
  emphasis?: "caveat";
  provenance: Provenance;
  prdRef: string;
}

export interface Criterion {
  parameter: Localized;
  cpcbClass: "B" | "D";
  rule: Localized;
  unit: string | null;
  role: "standard" | "severity_line";
}

export interface CoverageSummary {
  expectedCells: number;
  rowsInFile: number;
  absentCells: number;
  absentDetail: Localized;
  provenance: Provenance;
  prdRef: string;
}

export interface Meta {
  sourceKind: "backend";
  sourceLabel: Localized;
  prdVersion: string;
  analysisDate: string;
  visarjanDate: string;
  dataWindow: Localized;
  ghatCount: number;
  criteria: Criterion[];
  notAssessable: Localized;
  pagesVerified: boolean;
  /** Size of the partial manual PDF spot check, when the source has one. */
  spotCheck?: { readings: number; pages: number };
  sourcePdfs: Record<ReportYear, string>;
  trackRepoUrl: string;
  coverage: CoverageSummary;
}

/** How a reading is displayed. The backend assigns it from the CSV `flag` column per the data dictionary. */
export type ValueState = "numeric" | "bdl" | "nd" | "not_sampled" | "unknown_flag" | "invalid_value";

export interface TrackReading {
  id: string;
  csvLine: number;
  year: ReportYear;
  festival: "Ganesh" | "Durga";
  siteId: string;
  csvSiteName: string;
  waterBody: string;
  phase: "pre" | "during" | "after";
  parameter: string;
  value: number | null;
  valueAsPrinted: string;
  unitAssumed: string;
  flag: string;
  valueState: ValueState;
  parameterAsPrinted: string;
  siteAsPrinted: string;
  siteMatchConfidence: string;
  source: SourceRef | null;
  provenance: "backend";
  /** Backend Class B result for this reading (pass / fail / unassessable / no_criterion), when supplied. */
  classB?: string;
}

export interface TrackDataset {
  sourceFile: string;
  sourceRepo: string;
  sourceSha256: string;
  rowCount: number;
  transcribedOn: string;
  rows: TrackReading[];
}

export type Festival = TrackReading["festival"];
export type Phase = TrackReading["phase"];

export interface Season {
  year: ReportYear;
  festival: Festival;
}

/** A cell's display state. `no_table` marks an expected cell with no row in the CSV at all. */
export type CellState = ValueState | "no_table";

/**
 * One cell of the expected grid (season × phase × parameter) for a site.
 * Cells with a CSV row carry the reading; cells without one are `no_table`.
 */
export interface GridCell {
  key: string;
  year: ReportYear;
  festival: Festival;
  phase: Phase;
  parameter: string;
  state: CellState;
  reading?: TrackReading;
  /** Why a `no_table` cell has no row: the whole season's table is absent, or this parameter is absent from it. */
  missingReason?: "season_table_absent" | "parameter_absent";
}

export interface PrintedName {
  name: string;
  seasons: Season[];
}

export interface SiteEvidence {
  siteId: string;
  seasons: Season[];
  phases: Phase[];
  parameters: string[];
  cells: GridCell[];
  printedNames: PrintedName[];
  /** False when the grid comes from the backend export (always, now). */
  assembledFromTranscription: boolean;
}

export type TaskGroup = "aeration" | "cleaning" | "barricading" | "sampling" | "identity";

/** A recommended action from PRD v2 §7.2, for officer verification. */
export interface RecommendedAction {
  id: string;
  /** The flag that triggers it, or "ALL" for actions that apply to every ghat. */
  trigger: FlagCode | "ALL";
  taskGroup: TaskGroup;
  text: Localized;
  /** PRD window relative to D = 20 Oct 2026, e.g. "D-3 → D+7". */
  window: string;
  dates: Localized;
  /** ISO dates of the window (inclusive). */
  start: string;
  end: string;
  sourceStatus: Localized;
  verified: boolean;
  provenance: Provenance;
  prdRef: string;
  /** All triggering flags (a rule can match several), when supplied by the backend. */
  triggers?: string[];
  /** False while the Hindi text is a provisional translation. */
  hiReviewed?: boolean;
  /** Role from config/ghat_assignments.csv, or null when unassigned. */
  responsible?: string | null;
  /** True when that role is a documented assumption to confirm. */
  responsibleIsAssumption?: boolean;
}

export interface TargetItem {
  id: "do" | "bod" | "ph" | "coliform";
  parameter: Localized;
  target: Localized;
  inCurrentData: boolean;
}

/** The 27 Oct standard from PRD v2 §7.1. */
export interface TargetStandard {
  sampleDate: string;
  items: TargetItem[];
  statuses: { id: string; label: Localized; rule: Localized }[];
  interimNote: Localized;
  currentStatus: Localized;
  provenance: Provenance;
  prdRef: string;
}

/** A window of the PRD v2 §7.3 day-by-day plan. */
export interface PlanWindow {
  id: string;
  label: string;
  dates: Localized;
  start: string;
  end: string;
  activities: Localized;
}

/** Per task group: PRD v2 §7.4 role example (not an assignment) and the report-back outcome. */
export interface TaskGroupInfo {
  group: TaskGroup;
  roleExample: Localized;
  outcome: Localized;
}

export interface WorkOrderMeta {
  issuedByRole: Localized;
  reportBackBy: Localized;
  reportBackItems: Localized[];
  provenance: Provenance;
  prdRef: string;
}

/** Estimator line items (PRD v2 §8.3). Rates are blank until entered. */
export interface EstimateLine {
  id: string;
  item: Localized;
  unit: Localized;
}

/** Everything the UI can ask for; implemented by lib/data/backend.ts. */
export interface DataSource {
  getMeta(): Promise<Meta>;
  getRanking(): Promise<SiteRanking[]>;
  getSite(siteId: string): Promise<SiteRanking | undefined>;
  getHeadlines(): Promise<HeadlineFinding[]>;
  getTrackDataset(): Promise<TrackDataset>;
  getSiteEvidence(siteId: string): Promise<SiteEvidence | undefined>;
  getRecommendedActions(siteId: string): Promise<RecommendedAction[]>;
  getTargetStandard(): Promise<TargetStandard>;
  getPlanWindows(): Promise<PlanWindow[]>;
  getTaskGroups(): Promise<TaskGroupInfo[]>;
  getWorkOrderMeta(): Promise<WorkOrderMeta>;
  getEstimateLines(): Promise<EstimateLine[]>;
}
