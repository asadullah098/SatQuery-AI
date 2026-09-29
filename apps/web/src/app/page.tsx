import Link from "next/link";
import dynamic from "next/dynamic";
import { ArrowRight, BadgeCheck, BrainCircuit, Braces, Focus, GitBranch, Orbit, Radar, ScanLine, ScanSearch, ShieldCheck, UploadCloud } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { TiltSurface } from "@/components/tilt-surface";

const SatelliteScene = dynamic(() => import("@/components/satellite-scene"), {
  loading: () => <div className="scene-poster" aria-label="Loading orbital observation sequence" />,
});

const capabilities = [
  { icon: Radar, title: "Multisensor by design", text: "Fuses Sentinel-1 SAR with Sentinel-2 multispectral observations instead of flattening them into generic RGB." },
  { icon: Focus, title: "Evidence attached", text: "Answers carry modality provenance, spatial evidence when supported, confidence method, and processing history." },
  { icon: Braces, title: "Auditable routing", text: "Input contracts and task capabilities determine which specialist runs—and why incompatible requests stop early." },
];
const workflow = [
  { icon: UploadCloud, label: "Observe", detail: "Load paired S1 + S2 assets" },
  { icon: BadgeCheck, label: "Validate", detail: "Inspect format, bands and alignment" },
  { icon: GitBranch, label: "Route", detail: "Match task to a compatible specialist" },
  { icon: BrainCircuit, label: "Reason", detail: "Run multisensor model inference" },
  { icon: ScanLine, label: "Verify", detail: "Return evidence, uncertainty and trace" },
];

export default function Home() {
  return (
    <main id="main-content">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <nav className="nav" aria-label="Primary navigation">
        <Link className="brand" href="/" aria-label="SatQuery AI home">
          <span className="brand-mark"><Orbit aria-hidden="true" size={20} /></span>
          <span>SatQuery <b>AI</b></span>
        </Link>
        <div className="nav-links">
          <a href="#system">System</a>
          <a href="#capabilities">Capabilities</a>
          <Link href="/models">Models</Link>
          <Link href="/runs">Runs</Link>
          <ThemeToggle />
          <Link className="button button-small" href="/workspace">Open workspace <ArrowRight aria-hidden="true" size={16} /></Link>
        </div>
      </nav>

      <section className="hero hero-cinematic" aria-label="From orbit to Earth observation">
        <div className="hero-visual" aria-hidden="true">
          <SatelliteScene />
        </div>
        <div className="hero-content shell">
          <div className="hero-copy">
            <div className="eyebrow"><span className="pulse-dot" /> Primary route ready for integration</div>
            <h1>Ask the Earth.<br /><span>See the evidence.</span></h1>
            <p>SatQuery turns natural-language questions into auditable Sentinel-1 and Sentinel-2 analysis through an RS-InternVL multisensor workflow.</p>
            <div className="hero-actions">
              <Link className="button" href="/workspace">Launch workspace <ArrowRight aria-hidden="true" size={18} /></Link>
              <a className="text-link" href="#system">Explore the system <span aria-hidden="true">↓</span></a>
            </div>
            <dl className="hero-metrics" aria-label="System highlights">
              <div><dt>Inputs</dt><dd>S1 + S2</dd></div>
              <div><dt>Primary model</dt><dd>RS-InternVL</dd></div>
              <div><dt>Outputs</dt><dd>Answer + evidence</dd></div>
            </dl>
          </div>
        </div>
      </section>

      <section className="workflow-ribbon" aria-labelledby="workflow-title">
        <div className="workflow-intro shell"><span className="kicker">From pixels to proof</span><h2 id="workflow-title">One traceable intelligence loop.</h2></div>
        <ol className="workflow-steps shell">
          {workflow.map(({ icon: Icon, label, detail }, index) => <li key={label}><div className="workflow-node"><span>0{index + 1}</span><Icon aria-hidden="true" /></div><div><strong>{label}</strong><p>{detail}</p></div></li>)}
        </ol>
      </section>

      <section className="system-section shell" id="system">
        <div className="section-heading">
          <div><span className="kicker">The primary route</span><h2>Two sensors. One accountable answer.</h2></div>
          <p>The controller checks the assets and task before inference, keeping the system grounded in what the selected model can actually process.</p>
        </div>
        <div className="pipeline" role="img" aria-label="Sentinel-1 and Sentinel-2 inputs pass through validation into RS-InternVL and produce an evidence-grounded result">
          <div className="sensor-card sar"><Radar aria-hidden="true" /><span>Sentinel-1</span><strong>SAR</strong><small>Structure · moisture · texture</small></div>
          <div className="flow-line"><span>Validated pair</span></div>
          <div className="model-core"><ScanSearch aria-hidden="true" /><span>PRIMARY MODEL</span><strong>RS-InternVL</strong><small>Multisensor reasoning</small></div>
          <div className="flow-line"><span>Normalized result</span></div>
          <div className="result-card"><ShieldCheck aria-hidden="true" /><span>OUTPUT</span><strong>Answer + evidence</strong><small>Confidence · provenance · trace</small></div>
          <div className="sensor-card optical"><Orbit aria-hidden="true" /><span>Sentinel-2</span><strong>Multispectral</strong><small>Land cover · water · vegetation</small></div>
        </div>
      </section>

      <section className="capabilities shell" id="capabilities">
        <div className="section-heading compact"><div><span className="kicker">Built for scientific trust</span><h2>Every decision stays inspectable.</h2></div></div>
        <div className="capability-grid">
          {capabilities.map(({ icon: Icon, title, text }, index) => (
            <TiltSurface key={title}><article className="capability-card">
              <div className="card-index">0{index + 1}</div><Icon aria-hidden="true" />
              <h3>{title}</h3><p>{text}</p>
            </article></TiltSurface>
          ))}
        </div>
      </section>

      <section className="cta shell">
        <div className="cta-orbit" aria-hidden="true"><i /><i /><span><ScanSearch /></span></div>
        <div className="cta-content"><span className="kicker">Mission control is online</span><h2>Start with the evidence.</h2><p>Load a sensor pair, ask a question, and inspect every decision—from validation to model output.</p><div className="cta-trust"><span><ShieldCheck /> Capability checked</span><span><Radar /> S1 + S2 ready</span></div></div>
        <Link className="button cta-button" href="/workspace">Open analysis workspace <ArrowRight aria-hidden="true" /></Link>
      </section>

      <footer className="footer shell"><span>SatQuery AI · SIH research prototype</span><span>RS-InternVL primary route</span></footer>
    </main>
  );
}
