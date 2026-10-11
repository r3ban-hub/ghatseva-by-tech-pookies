// The single entry point screens use for data. The source is the Python backend export
// (lib/data/generated/backend.json, written by `python -m ghatwatch.export_web`), mapped to
// the UI's shapes in ./backend. Screens never compute rankings, flags, limits or dates.

import type { DataSource } from "./types";
import { backendSource } from "./backend";

const source: DataSource = backendSource;

export const getMeta = () => source.getMeta();
export const getRanking = () => source.getRanking();
export const getSite = (siteId: string) => source.getSite(siteId);
export const getHeadlines = () => source.getHeadlines();
export const getTrackDataset = () => source.getTrackDataset();
export const getSiteEvidence = (siteId: string) => source.getSiteEvidence(siteId);
export const getRecommendedActions = (siteId: string) => source.getRecommendedActions(siteId);
export const getTargetStandard = () => source.getTargetStandard();
export const getPlanWindows = () => source.getPlanWindows();
export const getTaskGroups = () => source.getTaskGroups();
export const getWorkOrderMeta = () => source.getWorkOrderMeta();
export const getEstimateLines = () => source.getEstimateLines();
export const getIllustrativeValues = () => source.getIllustrativeValues();

export type * from "./types";
