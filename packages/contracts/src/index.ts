export type Modality = "S1_SAR" | "S2_MULTISPECTRAL" | "RGB" | "UNKNOWN";
export type Task = "vqa" | "caption" | "grounding" | "change";
export interface ModelCapability { id: string; displayName: string; status: "mock" | "available" | "unavailable"; modalities: Modality[][]; tasks: Task[]; temporal: boolean; outputTypes: ("text" | "bbox" | "mask")[]; version: string; }
export interface AnalysisRequest { assetIds: string[]; query: string; requestedTask?: "auto" | Task; }
export interface AnalysisResult { runId: string; answer: string; task: Task; model: { id: string; version: string }; confidence?: { value: number; method: string; calibrated: boolean }; warnings: string[]; trace: Array<{ stage: string; status: string; detail: string }>; }
