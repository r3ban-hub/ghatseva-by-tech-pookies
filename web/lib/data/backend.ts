// DataSource backed by the Python backend export (lib/data/generated/backend.json).
// Regenerate the export with `python -m ghatwatch.export_web` from the repository root.
// Every figure, flag, note, reading, grid cell, action and date comes from the export;
// this file only maps it to the UI's shapes and adds presentation text from ./static.

import raw from "./generated/backend.json";
import type {
  Criterion,
  DataSource,
  GridCell,
  HeadlineFinding,
  Localized,
  Meta,
  PlanWindow,
  PrintedName,
  RecommendedAction,
  ReportYear,
  Season,
  SiteEvidence,
  SiteRanking,
  SourceRef,
  TargetStandard,
  TaskGroup,
  TrackDataset,
  TrackReading,
  FlagCode,
  ValueState,
  CellState,
} from "./types";
import {
  DATA_WINDOW,
  ESTIMATE_LINES,
  PARAMETERS,
  PARAMETER_LABELS,
  PHASES,
  PLAN_WINDOW_TEXT,
  SEASONS,
  SITE_LABELS,
  SOURCE_LABEL,
  TARGET_STATUSES,
  TASK_GROUPS,
  WATER_BODY_HI,
  WORK_ORDER_META,
} from "./static";

// ---------------------------------------------------------------- export shape

interface ExportRef { year: number; page: number; verified: boolean }
interface ExportFrac { n: number; N: number }
interface ExportReading {
  csvLine: number; waterBody: string; value: number | null; valueAsPrinted: string; unitAssumed: string; flag: string;
  parameterAsPrinted: string; siteAsPrinted: string; siteMatchConfidence: string; page: number | null;
  spotChecked: boolean; classB: string; contradictory: boolean;
}
interface ExportCell {
  year: number; festival: "Ganesh" | "Durga"; site: string; phase: "pre" | "during" | "after"; parameter: string;
  state: CellState; reading?: ExportReading; missingReason?: "season_table_absent" | "parameter_absent";
}
interface ExportSite {
  csvSiteName: string; rank: number; tier: 1 | 2 | 3 | 4; highRisk: boolean; waterBody: string | null;
  identityConfidence: "high" | "medium"; doBelow5: ExportFrac; doBelow4: number; doMin: string; doZeroCount: number;
  bodAbove3: ExportFrac; phOutOfRange: ExportFrac; expectedPerParameter: number; flags: FlagCode[];
  notes: { flag: FlagCode; en: string; hi: string; refs: ExportRef[] }[];
}
interface ExportAction {
  order: number; site: string; id: string; trigger: FlagCode | "ALL"; triggers: string[]; taskGroup: TaskGroup;
  en: string; hi: string; hiReviewed: boolean; window: string; start: string; end: string; datesEn: string; datesHi: string;
  source: string; verified: boolean; warning: string | null;
  responsible: string; responsibleAssigned: boolean; responsibleIsAssumption: boolean; reportTo: string | null;
}
interface ExportCriterion {
  parameter: string; cpcbClass: "B" | "D"; limitType: "min" | "max" | "range"; limit: string; unit: string | null;
  role: "standard" | "severity_line"; ruleEn: string; ruleHi: string;
}
interface BackendExport {
  generator: { generatedOn: string; readingsFile: string; readingsSha256: string; trackPackUrl: string };
  meta: {
    visarjanDate: string; d7Date: string; ghatCount: number; criteria: ExportCriterion[]; coliform: Localized;
    coverage: { expectedCells: number; rowsInFile: number; absentCells: number; absentDetail: Localized };
    spotCheck: { readings: number; pages: number }; sourcePdfs: Record<string, string>; interimNote: Localized;
    warningEn: string; warningHi: string;
  };
  headlines: {
    doBelow5: ExportFrac; doBelow4: ExportFrac; doZero: { count: number; sites: string[]; refs: ExportRef[] };
    bodAbove3: ExportFrac; phOut: ExportFrac; durgaDoBelow5: ExportFrac; durgaBodAbove3: ExportFrac;
    highRisk: ExportFrac; preBodAbove3: ExportFrac;
  };
  sites: ExportSite[];
  cells: ExportCell[];
  actions: ExportAction[];
  targets: { parameter: string; en: string; hi: string; inCurrentData: boolean }[];
  planWindows: { start: string; end: string; datesEn: string; datesHi: string }[];
}

const data = raw as unknown as BackendExport;
validateExport(data);

/** Checks the fields the UI relies on, so a renamed or mistyped field fails the build instead of rendering wrong. */
function validateExport(d: BackendExport): void {
  const fail = (what: string): never => {
    throw new Error(`backend.json does not match the UI contract (${what}). Regenerate it: python -m ghatwatch.export_web`);
  };
  const ISO = /^\d{4}-\d{2}-\d{2}$/;
  const STATES = new Set(["numeric", "bdl", "nd", "not_sampled", "no_table", "unknown_flag", "invalid_value"]);
  const GROUPS = new Set(["aeration", "cleaning", "barricading", "sampling", "identity"]);
  const FLAGS = new Set(["DO_SEVERE", "DO_ZERO", "DO_OFTEN_LOW", "BOD_OFTEN_HIGH", "PH_OUT", "DATA_GAP", "SITE_IDENTITY"]);
  const isFrac = (f: unknown) => typeof f === "object" && f !== null && typeof (f as ExportFrac).n === "number" && typeof (f as ExportFrac).N === "number";
  for (const key of ["generator", "meta", "headlines", "sites", "cells", "actions", "targets", "planWindows"]) {
    if (!(key in d)) fail(`missing "${key}"`);
  }
  d.sites.forEach((s, i) => {
    if (typeof s.csvSiteName !== "string") fail(`sites[${i}].csvSiteName`);
    if (![1, 2, 3, 4].includes(s.tier)) fail(`sites[${i}].tier = ${String(s.tier)}`);
    for (const k of ["doBelow5", "bodAbove3", "phOutOfRange"] as const) if (!isFrac(s[k])) fail(`sites[${i}].${k}`);
    for (const k of ["rank", "doBelow4", "doZeroCount", "expectedPerParameter"] as const) if (typeof s[k] !== "number") fail(`sites[${i}].${k}`);
    if (typeof s.doMin !== "string" || typeof s.highRisk !== "boolean") fail(`sites[${i}].doMin / highRisk`);
    if (!Array.isArray(s.flags) || s.flags.some((f) => !FLAGS.has(f))) fail(`sites[${i}].flags`);
    if (!Array.isArray(s.notes) || s.notes.some((n) => !FLAGS.has(n.flag) || typeof n.en !== "string" || typeof n.hi !== "string")) fail(`sites[${i}].notes`);
  });
  d.cells.forEach((c, i) => {
    if (!STATES.has(c.state)) fail(`cells[${i}].state = ${String(c.state)}`);
    if (c.state === "no_table" ? !(c.missingReason === "season_table_absent" || c.missingReason === "parameter_absent") : !c.reading) {
      fail(`cells[${i}] reading / missingReason`);
    }
  });
  d.actions.forEach((a, i) => {
    if (!(a.trigger === "ALL" || FLAGS.has(a.trigger))) fail(`actions[${i}].trigger = ${String(a.trigger)}`);
    if (!GROUPS.has(a.taskGroup)) fail(`actions[${i}].taskGroup = ${String(a.taskGroup)}`);
    if (!ISO.test(a.start) || !ISO.test(a.end)) fail(`actions[${i}] dates`);
  });
  if (!ISO.test(d.meta.visarjanDate) || !ISO.test(d.meta.d7Date)) fail("meta dates");
  if (!d.meta.interimNote?.en || !d.meta.coverage || !Array.isArray(d.meta.criteria)) fail("meta.interimNote / coverage / criteria");
  for (const k of ["doBelow5", "doBelow4", "bodAbove3", "phOut", "durgaDoBelow5", "durgaBodAbove3", "highRisk", "preBodAbove3"] as const) {
    if (!isFrac(d.headlines[k])) fail(`headlines.${k}`);
  }
  if (!Array.isArray(d.headlines.doZero?.sites) || !Array.isArray(d.headlines.doZero?.refs)) fail("headlines.doZero");
}

// ---------------------------------------------------------------- helpers

function siteLabel(csvSiteName: string) {
  const label = SITE_LABELS[csvSiteName];
  if (!label) throw new Error(`backend.json names a site with no UI label: "${csvSiteName}"`);
  return label;
}

function sourceRef(r: ExportRef): SourceRef {
  const year = r.year as ReportYear;
  return { year, page: r.page, pdf: data.meta.sourcePdfs[String(r.year)], verified: r.verified };
}

const criterion = (parameter: string, cls: "B" | "D") => {
  const c = data.meta.criteria.find((x) => x.parameter === parameter && x.cpcbClass === cls);
  if (!c) throw new Error(`backend.json has no Class ${cls} criterion for ${parameter}`);
  return c;
};
const unitOf = (c: ExportCriterion) => (c.unit ? ` ${c.unit}` : "");
const DO_B = criterion("Dissolved oxygen", "B");
const DO_D = criterion("Dissolved oxygen", "D");
const BOD_B = criterion("BOD", "B");
const PH_B = criterion("pH", "B");
const PH_RANGE = PH_B.limit.replace("-", "–");

const SITES: SiteRanking[] = [...data.sites]
  .sort((a, b) => a.rank - b.rank)
  .map((s) => {
    const label = siteLabel(s.csvSiteName);
    const wb = s.waterBody ?? "";
    return {
      siteId: label.siteId,
      name: { en: s.csvSiteName, hi: label.hi },
      csvSiteName: s.csvSiteName,
      waterBody: { en: wb, hi: WATER_BODY_HI[wb] ?? wb },
      identityConfidence: s.identityConfidence,
      rank: s.rank,
      tier: s.tier,
      highRisk: s.highRisk,
      doBelow5: s.doBelow5,
      doBelow4: s.doBelow4,
      doMin: s.doMin,
      doZeroCount: s.doZeroCount,
      bodAbove3: s.bodAbove3,
      phOutOfRange: s.phOutOfRange,
      expectedPerParameter: s.expectedPerParameter,
      flags: s.flags,
      notes: s.notes.map((n) => ({ flag: n.flag, text: { en: n.en, hi: n.hi }, refs: n.refs.map(sourceRef), provenance: "backend" as const })),
      provenance: "backend",
      prdRef: "ranking.py",
    };
  });

const siteIdOf = (csvSiteName: string) => siteLabel(csvSiteName).siteId;
const readingId = (c: ExportCell) =>
  `${c.year}-${c.festival}-${siteIdOf(c.site)}-${c.phase}-${c.parameter}`.toLowerCase().replace(/\s+/g, "-");

function toReading(c: ExportCell): TrackReading {
  const r = c.reading!;
  const year = c.year as ReportYear;
  return {
    id: readingId(c),
    csvLine: r.csvLine,
    year,
    festival: c.festival,
    siteId: siteIdOf(c.site),
    csvSiteName: c.site,
    waterBody: r.waterBody,
    phase: c.phase,
    parameter: c.parameter,
    value: r.value,
    valueAsPrinted: r.valueAsPrinted,
    unitAssumed: r.unitAssumed,
    flag: r.flag,
    valueState: c.state as ValueState,
    parameterAsPrinted: r.parameterAsPrinted,
    siteAsPrinted: r.siteAsPrinted,
    siteMatchConfidence: r.siteMatchConfidence,
    source: r.page === null ? null : { year, page: r.page, pdf: data.meta.sourcePdfs[String(year)], verified: r.spotChecked },
    provenance: "backend",
    classB: r.classB,
  };
}

const READINGS: TrackReading[] = data.cells.filter((c) => c.reading).map(toReading);
const READING_BY_ID = new Map(READINGS.map((r) => [r.id, r]));

function siteEvidence(siteId: string): SiteEvidence | undefined {
  const site = SITES.find((s) => s.siteId === siteId);
  if (!site) return undefined;
  const byKey = new Map(
    data.cells.filter((c) => c.site === site.csvSiteName).map((c) => [`${c.year}|${c.festival}|${c.phase}|${c.parameter}`, c]),
  );
  const cells: GridCell[] = [];
  for (const season of SEASONS) {
    for (const parameter of PARAMETERS) {
      for (const phase of PHASES) {
        const c = byKey.get(`${season.year}|${season.festival}|${phase}|${parameter}`);
        if (!c) throw new Error(`backend.json lacks grid cell ${site.csvSiteName} ${season.year} ${season.festival} ${phase} ${parameter}`);
        const key = `${season.year}-${season.festival}-${phase}-${parameter}`.toLowerCase().replace(/\s+/g, "-");
        cells.push(
          c.reading
            ? { key, ...season, phase, parameter, state: c.state, reading: READING_BY_ID.get(readingId(c)) }
            : { key, ...season, phase, parameter, state: "no_table", missingReason: c.missingReason },
        );
      }
    }
  }
  const printed = new Map<string, Season[]>();
  for (const season of SEASONS) {
    const names = new Set(
      READINGS.filter((r) => r.siteId === siteId && r.year === season.year && r.festival === season.festival).map((r) => r.siteAsPrinted),
    );
    for (const name of names) printed.set(name, [...(printed.get(name) ?? []), season]);
  }
  const printedNames: PrintedName[] = [...printed].map(([name, seasons]) => ({ name, seasons }));
  return { siteId, seasons: SEASONS, phases: PHASES, parameters: PARAMETERS, cells, printedNames, assembledFromTranscription: false };
}

function actions(siteId: string): RecommendedAction[] {
  const site = SITES.find((s) => s.siteId === siteId);
  if (!site) return [];
  return data.actions
    .filter((a) => a.site === site.csvSiteName)
    .sort((a, b) => a.order - b.order)
    .map((a) => ({
      id: a.id,
      trigger: a.trigger,
      taskGroup: a.taskGroup,
      text: { en: a.en, hi: a.hi },
      window: a.window,
      dates: { en: a.datesEn, hi: a.datesHi },
      start: a.start,
      end: a.end,
      sourceStatus: {
        en: a.warning ? `${a.warning} Source: ${a.source}.` : `Source: ${a.source}.`,
        hi: a.warning ? `${data.meta.warningHi}। स्रोत: ${a.source}।` : `स्रोत: ${a.source}।`,
      },
      verified: a.verified,
      provenance: "backend",
      prdRef: "action_rules.csv",
      triggers: a.triggers,
      hiReviewed: a.hiReviewed,
      responsible: a.responsibleAssigned ? a.responsible : null,
      responsibleIsAssumption: a.responsibleIsAssumption,
    }));
}

const frac = (f: ExportFrac) => ({ kind: "fraction" as const, value: { n: f.n, N: f.N } });
const h = data.headlines;
const HEADLINES: HeadlineFinding[] = [
  {
    id: "do-below-5",
    label: { en: `Dissolved oxygen below ${DO_B.limit}${unitOf(DO_B)} (Class B)`, hi: `घुलित ऑक्सीजन ${DO_B.limit}${unitOf(DO_B)} से कम (क्लास B)` },
    value: frac(h.doBelow5),
    detail: { en: `numeric DO readings, all ${data.meta.ghatCount} ghats`, hi: `संख्यात्मक DO रीडिंग, सभी ${data.meta.ghatCount} घाट` },
    provenance: "backend",
    prdRef: "criteria.py",
  },
  {
    id: "do-below-4",
    label: { en: `Dissolved oxygen below ${DO_D.limit}${unitOf(DO_D)} (Class D line)`, hi: `घुलित ऑक्सीजन ${DO_D.limit}${unitOf(DO_D)} से कम (क्लास D रेखा)` },
    value: frac(h.doBelow4),
    detail: { en: "numeric DO readings", hi: "संख्यात्मक DO रीडिंग" },
    provenance: "backend",
    prdRef: "criteria.py",
  },
  {
    id: "do-zero",
    label: { en: `Dissolved oxygen read 0${unitOf(DO_B)}`, hi: `घुलित ऑक्सीजन 0${unitOf(DO_B)} दर्ज` },
    value: { kind: "count", value: h.doZero.count },
    detail: h.doZero.sites.length === 1
      ? { en: `readings, all at ${h.doZero.sites[0]}`, hi: `रीडिंग, सभी ${siteLabel(h.doZero.sites[0]).hi} पर` }
      : h.doZero.sites.length > 1
      ? { en: `readings at ${h.doZero.sites.join(", ")}`, hi: `रीडिंग: ${h.doZero.sites.map((s) => siteLabel(s).hi).join(", ")}` }
      : { en: "readings", hi: "रीडिंग" },
    refs: h.doZero.refs.map(sourceRef),
    provenance: "backend",
    prdRef: "ranking.py",
  },
  {
    id: "bod-above-3",
    label: { en: `BOD above ${BOD_B.limit}${unitOf(BOD_B)} (Class B)`, hi: `BOD ${BOD_B.limit}${unitOf(BOD_B)} से अधिक (क्लास B)` },
    value: frac(h.bodAbove3),
    detail: { en: `numeric BOD readings, all ${data.meta.ghatCount} ghats`, hi: `संख्यात्मक BOD रीडिंग, सभी ${data.meta.ghatCount} घाट` },
    provenance: "backend",
    prdRef: "criteria.py",
  },
  {
    id: "ph-out",
    label: { en: `pH outside ${PH_RANGE} (Class B)`, hi: `pH ${PH_RANGE} से बाहर (क्लास B)` },
    value: frac(h.phOut),
    detail: { en: "numeric pH readings", hi: "संख्यात्मक pH रीडिंग" },
    provenance: "backend",
    prdRef: "criteria.py",
  },
  {
    id: "durga-only",
    label: {
      en: `Durga readings only: DO below ${DO_B.limit} / BOD above ${BOD_B.limit}`,
      hi: `केवल दुर्गा रीडिंग: DO ${DO_B.limit} से कम / BOD ${BOD_B.limit} से अधिक`,
    },
    value: frac(h.durgaDoBelow5),
    detail: {
      en: `DO readings below ${DO_B.limit}; BOD was above ${BOD_B.limit} in ${h.durgaBodAbove3.n} of ${h.durgaBodAbove3.N} Durga readings`,
      hi: `DO रीडिंग ${DO_B.limit} से कम; दुर्गा की ${h.durgaBodAbove3.N} में से ${h.durgaBodAbove3.n} BOD रीडिंग ${BOD_B.limit} से अधिक`,
    },
    provenance: "backend",
    prdRef: "criteria.py",
  },
  {
    id: "high-risk",
    label: { en: "Ghats flagged high risk", hi: "उच्च जोखिम चिह्नित घाट" },
    value: frac(h.highRisk),
    detail: {
      en: `high risk = any DO below ${DO_D.limit}, or DO below ${DO_B.limit} in more than half of readings`,
      hi: `उच्च जोखिम = कोई भी DO ${DO_D.limit} से कम, या आधे से अधिक रीडिंग में DO ${DO_B.limit} से कम`,
    },
    provenance: "backend",
    prdRef: "ranking.py",
  },
  {
    id: "pre-immersion-bod",
    label: { en: `BOD already above ${BOD_B.limit} before immersion`, hi: `विसर्जन से पहले ही BOD ${BOD_B.limit} से अधिक` },
    value: frac(h.preBodAbove3),
    detail: {
      en: "pre-immersion readings. BOD was already above the limit in most readings taken before immersion, so these readings cannot show what immersion itself changed.",
      hi: "विसर्जन-पूर्व रीडिंग। विसर्जन से पहले ली गई अधिकांश रीडिंग में BOD पहले ही सीमा से ऊपर था, इसलिए ये रीडिंग यह नहीं दिखा सकतीं कि विसर्जन से स्वयं क्या बदला।",
    },
    emphasis: "caveat",
    provenance: "backend",
    prdRef: "criteria.py",
  },
];

const CRITERIA: Criterion[] = data.meta.criteria.map((c) => ({
  parameter: PARAMETER_LABELS[c.parameter] ?? { en: c.parameter, hi: c.parameter },
  cpcbClass: c.cpcbClass,
  rule:
    c.role === "severity_line"
      ? { en: `${c.ruleEn} (used only as a severity line)`, hi: `${c.ruleHi} (केवल गंभीरता रेखा के रूप में)` }
      : { en: c.ruleEn, hi: c.ruleHi },
  unit: c.unit,
  role: c.role,
}));

const META: Meta = {
  sourceKind: "backend",
  sourceLabel: SOURCE_LABEL,
  prdVersion: "PRD v2",
  analysisDate: data.generator.generatedOn,
  visarjanDate: data.meta.visarjanDate,
  dataWindow: DATA_WINDOW,
  ghatCount: data.meta.ghatCount,
  criteria: CRITERIA,
  notAssessable: {
    en: `Total coliform (Class B: ${data.meta.coliform.en}) is not in the data, so no ghat can be shown as meeting Class B in full.`,
    hi: `टोटल कोलीफॉर्म (क्लास B: ${data.meta.coliform.hi}) डेटा में नहीं है, इसलिए किसी भी घाट को पूर्ण रूप से क्लास B मानकों पर खरा नहीं दिखाया जा सकता।`,
  },
  pagesVerified: false,
  spotCheck: data.meta.spotCheck,
  sourcePdfs: data.meta.sourcePdfs as unknown as Record<ReportYear, string>,
  trackRepoUrl: data.generator.trackPackUrl,
  coverage: {
    expectedCells: data.meta.coverage.expectedCells,
    rowsInFile: data.meta.coverage.rowsInFile,
    absentCells: data.meta.coverage.absentCells,
    absentDetail: data.meta.coverage.absentDetail,
    provenance: "backend",
    prdRef: "load.py",
  },
};

const TRACK: TrackDataset = {
  sourceFile: data.generator.readingsFile,
  sourceRepo: data.generator.trackPackUrl,
  sourceSha256: data.generator.readingsSha256,
  rowCount: READINGS.length,
  transcribedOn: data.generator.generatedOn,
  rows: READINGS,
};

const TARGET_IDS: Record<string, "do" | "bod" | "ph" | "coliform"> = {
  "Dissolved oxygen": "do", BOD: "bod", pH: "ph", "Total coliform": "coliform",
};
const d7 = new Date(`${data.meta.d7Date}T00:00:00`);
const d7Day = d7.getDate();
const TARGET: TargetStandard = {
  sampleDate: data.meta.d7Date,
  items: data.targets.map((t) => ({
    id: TARGET_IDS[t.parameter],
    parameter: { en: t.parameter, hi: PARAMETER_LABELS[t.parameter]?.hi ?? t.parameter },
    target: { en: t.en, hi: t.hi },
    inCurrentData: t.inCurrentData,
  })),
  statuses: TARGET_STATUSES,
  interimNote: data.meta.interimNote,
  currentStatus: {
    en: `Not yet assessed: the one-week-after sample is due on ${d7Day} Oct ${d7.getFullYear()}. There are no 2026 readings in the supplied data.`,
    hi: `अभी आकलन नहीं हुआ: एक सप्ताह बाद का नमूना ${d7Day} अक्टूबर ${d7.getFullYear()} को होना है। दिए गए डेटा में 2026 की कोई रीडिंग नहीं है।`,
  },
  provenance: "prd",
  prdRef: "PRD v2 §7.1",
};

if (data.planWindows.length !== PLAN_WINDOW_TEXT.length) {
  throw new Error(`backend.json has ${data.planWindows.length} plan windows; static.ts describes ${PLAN_WINDOW_TEXT.length}`);
}
const PLAN_WINDOWS: PlanWindow[] = data.planWindows.map((w, i) => ({
  id: `w${i + 1}`,
  label: PLAN_WINDOW_TEXT[i].label,
  dates: { en: w.datesEn, hi: w.datesHi },
  start: w.start,
  end: w.end,
  activities: PLAN_WINDOW_TEXT[i].activities,
}));

export const backendSource: DataSource = {
  async getMeta() { return META; },
  async getRanking() { return SITES; },
  async getSite(siteId) { return SITES.find((s) => s.siteId === siteId); },
  async getHeadlines() { return HEADLINES; },
  async getTrackDataset() { return TRACK; },
  async getSiteEvidence(siteId) { return siteEvidence(siteId); },
  async getRecommendedActions(siteId) { return actions(siteId); },
  async getTargetStandard() { return TARGET; },
  async getPlanWindows() { return PLAN_WINDOWS; },
  async getTaskGroups() { return TASK_GROUPS; },
  async getWorkOrderMeta() { return WORK_ORDER_META; },
  async getEstimateLines() { return ESTIMATE_LINES; },
};
