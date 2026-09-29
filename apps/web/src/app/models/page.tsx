import Link from "next/link";
import { ArrowLeft, CheckCircle2, Clock3, FlaskConical, Radar } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

const models = [
  ["RS-InternVL", "S1 SAR + S2 multispectral", "VQA · Captioning · Grounding*", "Primary · artifact verification pending", "primary"],
  ["GeoChat", "Single RGB", "VQA · Captioning · Grounding", "Deferred specialist", "deferred"],
  ["TEOChat / ChangeChat", "Bi-temporal optical", "Temporal QA · Change analysis", "Deferred specialist", "deferred"],
  ["EarthDial", "RGB · MS · SAR · Temporal", "Unified experimental route", "Research candidate", "experiment"],
];

export default function ModelsPage() {
  return <main className="registry-page"><header className="workspace-header glass-bar"><Link href="/" className="icon-button" aria-label="Back to home"><ArrowLeft /></Link><div className="workspace-title"><span className="brand-mark"><Radar /></span><div><strong>Model registry</strong><small>Capability and readiness contracts</small></div></div><div className="workspace-actions"><ThemeToggle /></div></header><section className="registry-shell"><span className="kicker">Auditable routing</span><h1>Specialists, not guesses.</h1><p className="registry-intro">SatQuery chooses models from declared input and task contracts. The primary RS-InternVL route remains explicitly separated from future temporal and RGB specialists.</p><div className="registry-grid">{models.map(([name,input,tasks,status,state]) => <article className={`registry-card ${state}`} key={name}><div className="registry-icon">{state === "primary" ? <CheckCircle2 /> : state === "experiment" ? <FlaskConical /> : <Clock3 />}</div><span>{status}</span><h2>{name}</h2><dl><div><dt>Input contract</dt><dd>{input}</dd></div><div><dt>Tasks</dt><dd>{tasks}</dd></div></dl></article>)}</div></section></main>;
}
