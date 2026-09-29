"use client";

import Link from "next/link";
import { Activity, ArrowLeft, CheckCircle2, Clock3, Download, FileImage, FileUp, Layers3, Play, Radar, ScanSearch, ShieldCheck, Sparkles } from "lucide-react";
import { type ChangeEvent, useMemo, useState } from "react";
import { ThemeToggle } from "./theme-toggle";

type Asset = { id: string; name: string; modality: "S1 SAR" | "S2 Multispectral" | "Unknown"; size: string; serverValidated?: boolean; previewUrl?: string; metadata?: { crs?: string | null; band_count?: number; resolution?: number[]; bounds?: number[] } };
type ApiResult = { run_id: string; inference_mode?: string; answer: string; task: string; model?: { id: string; version: string }; confidence: { value: number; method: string; calibrated: boolean }; warnings: string[]; metrics?: Record<string, number>; trace: Array<{ stage: string; status: string; detail: string }> };
type RunState = "idle" | "running" | "complete" | "error";
type QueryRoute = { supported: boolean; task: string; route: string; inputs: string; helper: string };

function classifyLocalQuery(query: string): QueryRoute {
  const normalized = query.toLowerCase().replaceAll("-", " ");
  const grounding = /highlight|where|locate|identify|map|region|area/.test(normalized);
  if (/vegetation|vegetated|green\s*land|greenland|green area|greenness|crop|farm|agricultur|forest|plantation/.test(normalized)) {
    return { supported: true, task: grounding ? "Vegetation grounding" : "Vegetation analysis", route: "CPU vegetation index", inputs: "S2 + S1 context", helper: "Maps likely green vegetation from optical evidence and checks non-water SAR support." };
  }
  if (/water|river|lake|pond|flood|inundat|wetland/.test(normalized)) {
    return { supported: true, task: grounding ? "Water grounding" : "Water analysis", route: "CPU water index", inputs: "S1 + S2", helper: "Maps optical water response confirmed by low SAR backscatter." };
  }
  return { supported: false, task: query ? "Unsupported CPU query" : "Waiting for query", route: "No compatible CPU route", inputs: "Water or vegetation query", helper: "The no-GPU engine currently supports water/flood and vegetation/green-land mapping. Other semantic questions require a VLM." };
}
const demoAssets: Asset[] = [
  { id: "s1-demo", name: "S1_IW_GRDH_20240817.tif", modality: "S1 SAR", size: "412 MB" },
  { id: "s2-demo", name: "S2_L2A_20240818.tif", modality: "S2 Multispectral", size: "638 MB" },
];

export function WorkspaceClient() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [query, setQuery] = useState("");
  const [run, setRun] = useState<RunState>("idle");
  const [step, setStep] = useState(0);
  const [ingestion, setIngestion] = useState<"idle" | "uploading" | "validated" | "offline" | "error">("idle");
  const [pairIssues, setPairIssues] = useState<string[]>([]);
  const [result, setResult] = useState<ApiResult | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const [compare, setCompare] = useState(50);
  const route = useMemo(() => classifyLocalQuery(query), [query]);
  const ready = assets.length >= 2 && query.trim().length >= 8 && ingestion !== "error" && route.supported;
  const task = route.task;
  const sarAsset = assets.find(asset => asset.modality === "S1 SAR");
  const opticalAsset = assets.find(asset => asset.modality === "S2 Multispectral");
  const evidenceLabel = result?.metrics?.vegetation_coverage_percent !== undefined ? "Likely vegetation boundary" : "Water evidence boundary";

  async function addFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = [...(event.target.files ?? [])].slice(0, 2);
    event.target.value = "";
    if (!files.length) return;
    setIngestion("uploading");
    const fallback = files.map((file, index) => ({ id: `${file.name}-${file.size}`, name: file.name, modality: (index === 0 ? "S1 SAR" : "S2 Multispectral") as Asset["modality"], size: `${Math.max(1, Math.round(file.size / 1024 / 1024))} MB` }));
    try {
      const apiUrl = process.env.NEXT_PUBLIC_SATQUERY_API_URL ?? "http://localhost:8000";
      const uploaded = await Promise.all(files.map(async file => {
        const form = new FormData(); form.append("file", file);
        const response = await fetch(`${apiUrl}/api/v1/assets`, { method: "POST", body: form });
        if (!response.ok) throw new Error("Asset validation failed");
        const asset = await response.json() as { id: string; filename: string; size_bytes: number; modality: string; metadata?: Asset["metadata"] };
        const modality: Asset["modality"] = asset.modality === "S1_SAR" ? "S1 SAR" : asset.modality === "S2_MULTISPECTRAL" ? "S2 Multispectral" : "Unknown";
        return { id: asset.id, name: asset.filename, modality, size: `${Math.max(1, Math.round(asset.size_bytes / 1024 / 1024))} MB`, serverValidated: true, metadata: asset.metadata, previewUrl: `${apiUrl}/api/v1/assets/${asset.id}/preview` };
      }));
      const combined = [...assets];
      for (const asset of uploaded) {
        const sameModality = asset.modality !== "Unknown" ? combined.findIndex(item => item.modality === asset.modality) : -1;
        if (sameModality >= 0) combined[sameModality] = asset; else combined.push(asset);
      }
      const pair = combined.slice(-2);
      if (pair.length === 2) {
        const validation = await fetch(`${apiUrl}/api/v1/asset-pairs/validate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset_ids: pair.map(item => item.id) }) });
        const compatibility = await validation.json() as { compatible: boolean; issues?: string[] };
        setAssets(pair); setPairIssues(compatibility.issues ?? ["Pair validation could not be completed."]); setIngestion(compatibility.compatible ? "validated" : "error");
      } else {
        setAssets(pair); setPairIssues(["Add the corresponding S1 or S2 observation to complete the pair."]); setIngestion("error");
      }
    } catch (error) {
      setAssets([...assets, ...fallback].slice(-2)); setIngestion("offline");
      setPairIssues([error instanceof Error ? error.message : "API unavailable"]);
    }
    setRun("idle"); setResult(null); setAnalysisError("");
  }
  async function analyze() {
    if (!ready || run === "running") return;
    setRun("running"); setStep(1); setResult(null); setAnalysisError("");
    try {
      const apiUrl = process.env.NEXT_PUBLIC_SATQUERY_API_URL ?? "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/v1/runs`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset_ids: assets.map(item => item.id), query, requested_task: "auto" }) });
      if (!response.ok) {
        const payload = await response.json().catch(() => null) as { detail?: string } | null;
        throw new Error(payload?.detail ?? "Analysis request failed");
      }
      setStep(3); const data = await response.json() as ApiResult; setResult(data); setStep(4); setRun("complete");
    } catch (error) {
      setAnalysisError(error instanceof Error ? error.message : "The analysis could not be completed.");
      setRun("error");
    }
  }
  function loadDemo() { setAssets(demoAssets); setQuery("Use optical and SAR observations to identify water regions."); setRun("idle"); setResult(null); setAnalysisError(""); setPairIssues([]); setIngestion("idle"); }
  function downloadReport() {
    const report = { ...(result ?? {}), task, query, assets };
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "satquery-demo-report.json"; anchor.click(); URL.revokeObjectURL(url);
  }

  return <main className="workspace">
    <header className="workspace-header glass-bar">
      <Link href="/" className="icon-button" aria-label="Back to SatQuery home"><ArrowLeft aria-hidden="true" /></Link>
      <div className="workspace-title"><span className="brand-mark"><Radar aria-hidden="true" /></span><div><strong>Analysis workspace</strong><small>New investigation</small></div></div>
      <div className="workspace-actions"><Link href="/runs" className="tool-button"><Activity aria-hidden="true" /> Run archive</Link><div className="system-status"><span className="pulse-dot" /> CPU evidence route ready</div><ThemeToggle /></div>
    </header>
    <div className="workspace-grid">
      <aside className="panel asset-panel" aria-label="Input assets">
        <div className="panel-heading"><div><span className="kicker">01 · Inputs</span><h1>Observations</h1></div><label className="icon-button" aria-label="Add observations"><FileUp /><input type="file" multiple accept=".tif,.tiff,.png,.jpg,.jpeg" onChange={addFiles} hidden /></label></div>
        <label className="dropzone"><FileUp aria-hidden="true" /><strong>Drop satellite imagery</strong><span>GeoTIFF or preview imagery</span><small>Choose up to two files</small><input type="file" multiple accept=".tif,.tiff,.png,.jpg,.jpeg" onChange={addFiles} hidden /></label>
        <button className="demo-button" onClick={loadDemo}><Sparkles aria-hidden="true" /> Load demo S1/S2 pair</button>
        <div className={`ingestion-status ${ingestion}`} role="status">{ingestion === "uploading" ? "Uploading and inspecting metadata…" : ingestion === "validated" ? "Pair spatially compatible" : ingestion === "offline" ? "API offline — using local preview mode" : ingestion === "error" ? "Pair requires attention" : "Ready for observations"}</div>
        {!!pairIssues.length && <div className="compatibility-errors">{pairIssues.map(issue => <p key={issue}>{issue}</p>)}</div>}
        <div className="asset-list" aria-live="polite">{assets.map(asset => <article className="asset-item" key={asset.id}><FileImage aria-hidden="true" /><div><strong>{asset.name}</strong><span>{asset.modality} · {asset.size}{asset.metadata?.crs ? ` · ${asset.metadata.crs}` : ""}{asset.metadata?.band_count ? ` · ${asset.metadata.band_count} bands` : ""}</span></div><CheckCircle2 aria-label={asset.serverValidated ? "Server validated" : "Compatible preview"} /></article>)}</div>
        {!assets.length && <div className="empty-note"><Layers3 aria-hidden="true" /><p>Add a co-registered Sentinel-1 and Sentinel-2 pair to begin compatibility checks.</p></div>}
        <div className="validation-list"><div><span>Format</span><small>{assets.length ? "GeoTIFF accepted" : "Waiting"}</small></div><div><span>Modality</span><small>{assets.length === 2 ? "S1 + S2" : "Waiting"}</small></div><div><span>Alignment</span><small>{assets.length === 2 ? "Demo compatible" : "Waiting"}</small></div></div>
      </aside>
      <section className="viewer-panel" aria-label="Imagery viewer">
        <div className="viewer-toolbar"><div><strong>Evidence canvas</strong><span>{assets.length ? "Paired observation preview" : "No observation loaded"}</span></div><button className="tool-button"><Layers3 aria-hidden="true" /> Layers</button></div>
        {sarAsset?.previewUrl && opticalAsset?.previewUrl ? <div className={`evidence-map ${run === "complete" ? "has-evidence" : ""}`}>
          <div className="raster-layer raster-s1" style={{ backgroundImage: `url(${sarAsset.previewUrl})` }} />
          <div className="raster-layer raster-s2" style={{ backgroundImage: `url(${opticalAsset.previewUrl})`, clipPath: `inset(0 ${100 - compare}% 0 0)` }} />
          {run === "complete" && result?.inference_mode === "deterministic" && <div className="deterministic-mask" style={{ backgroundImage: `url(${(process.env.NEXT_PUBLIC_SATQUERY_API_URL ?? "http://localhost:8000")}/api/v1/runs/${result.run_id}/evidence.png)` }} />}
          <div className="compare-line" style={{ left: `${compare}%` }} /><input className="compare-slider" aria-label="Compare S1 and S2 imagery" type="range" min="0" max="100" value={compare} onChange={event => setCompare(Number(event.target.value))} /><div className="map-grid" />
          <div className="map-label label-sar">S1 SAR</div><div className="map-label label-s2">S2 MS</div><div className="map-legend"><i /> {run === "complete" ? evidenceLabel : "Drag to compare modalities"} <span>{run === "complete" ? "CPU EO result" : "Server previews"}</span></div>
        </div> : <div className="viewer-empty"><div className={`orbit-rings ${run === "running" ? "scanning" : ""}`}><ScanSearch aria-hidden="true" /></div><h2>{run === "running" ? "Analyzing the sensor pair" : assets.length ? "Ready for a query" : "Your evidence appears here"}</h2><p>{run === "running" ? ["Validating metadata…", "Classifying the task…", "Running CPU EO engine…", "Normalizing evidence…"][step - 1] : "Inspect S1/S2 imagery, compare modalities, and review model-supported regions without leaving the run."}</p></div>}
        <div className="coordinate-bar"><span>CRS {assets.length ? "EPSG:32643" : "—"}</span><span>LAT {assets.length ? "23.1764° N" : "—"}</span><span>LON {assets.length ? "77.4126° E" : "—"}</span><span>ZOOM {assets.length ? "11.2×" : "—"}</span></div>
      </section>
      <aside className="panel query-panel" aria-label="Query and result">
        <div className="panel-heading"><div><span className="kicker">02 · Query</span><h2>Ask SatQuery</h2></div><Activity aria-hidden="true" /></div>
        <label htmlFor="query">Natural-language question</label><textarea id="query" value={query} onChange={e => { setQuery(e.target.value); setRun("idle"); setResult(null); setAnalysisError(""); }} placeholder="Identify water or green vegetated regions…" rows={5} aria-describedby="query-helper" /><p className={`helper ${query && !route.supported ? "capability-warning" : ""}`} id="query-helper">{route.helper}</p>
        <div className="route-preview"><div><span>Detected task</span><strong>{task}</strong></div><div><span>Live route</span><strong>{route.route}</strong></div><div><span>Required inputs</span><strong>{route.inputs}</strong></div></div>
        <button className="button analyze-button" disabled={!ready || run === "running"} onClick={analyze}>{run === "running" ? <Clock3 aria-hidden="true" /> : <Play aria-hidden="true" />} {run === "running" ? "Analyzing…" : "Analyze observations"}</button>
        {run === "complete" && result ? <section className="result-panel" aria-live="polite"><div className="result-heading"><span><ShieldCheck aria-hidden="true" /> Evidence-grounded result</span><b>{Math.round(result.confidence.value * 100)}% <small>{result.inference_mode === "deterministic" ? "sensor support" : result.confidence.calibrated ? "calibrated" : "demo score"}</small></b></div><p>{result.answer}</p><div className="trace">{(result.trace.length ? result.trace : [{ stage: "validation" }, { stage: "classification" }, { stage: "routing" }, { stage: "normalization" }]).map(item => <span className="complete" key={item.stage}>{item.stage}</span>)}</div><button className="report-button" onClick={downloadReport}><Download aria-hidden="true" /> Download JSON report</button><small className="mock-warning">{result.warnings.join(" ")} {result.inference_mode === "deterministic" ? "CPU-derived result; no VLM was executed." : "Simulated result—not real RS-InternVL inference."}</small></section> : run === "error" ? <div className="analysis-error" role="alert"><strong>Analysis not completed</strong><span>{analysisError}</span></div> : <div className="readiness"><CheckCircle2 aria-hidden="true" /><div><strong>{route.supported ? "Compatible CPU analysis ready" : "Choose a supported question"}</strong><span>{route.helper}</span></div></div>}
      </aside>
    </div>
  </main>;
}
