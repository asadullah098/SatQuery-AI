# SatQuery AI — Persistent Project Context

> Read this before changing product scope, architecture, model routing, or research claims.

## Project summary

SatQuery AI is an SIH project for natural-language analysis of satellite imagery. Its differentiator is not a claim that one new VLM solves every remote-sensing configuration. It combines a remote-sensing-adapted multisensor model with an auditable, query-driven controller that validates inputs and chooses a compatible specialist.

The primary research and implementation model is RS-InternVL, adapted around paired Sentinel-1 SAR and Sentinel-2 multispectral imagery using the BigEarthNet.txt research direction. Its initial jobs are multisensor VQA and captioning, plus grounding only when verified release artifacts support it.

## Source context and authority

This project synthesizes remote sensing multimodal research including:

- RS-InternVL and BigEarthNet remote-sensing multimodal foundations
- Sentinel-1 SAR and Sentinel-2 multispectral co-registration methodologies

Requirements and committed architecture decisions take precedence. Statements about public repositories, checkpoints, licenses, performance, and hardware remain hypotheses until independently verified and recorded.

## Non-negotiable scientific position

- BigEarthNet.txt is the foundation for S1/S2 multisensor adaptation, not for all seven proposed input configurations.
- RS-InternVL is the primary SatQuery model for joint multispectral + SAR understanding.
- Temporal change analysis is a separate capability requiring temporal models/datasets.
- The controller selects specialists by task and compatible inputs; it does not arbitrarily call models.
- Evidence, provenance, limitations, and confidence methodology are part of the output.
- A mock adapter is valuable for application development but must always be labeled as simulated.
- No public-artifact, benchmark, or capability claim is considered confirmed until its source is recorded.

## Input configurations from the research

| Configuration | Intended route | MVP state |
|---|---|---|
| Single RGB/optical | GeoChat or EarthDial candidate | Deferred |
| Single multispectral | RS-InternVL S2-capable path | Secondary |
| Single SAR | RS-InternVL-derived S1 or EarthDial candidate | Deferred |
| Co-registered multispectral + SAR | **RS-InternVL** | **Primary** |
| Bi-temporal optical/multispectral | TEOChat or ChangeChat | Deferred |
| Bi-temporal SAR | EarthDial/custom research | Experimental |
| Bi-temporal cross-modal | EarthDial/custom RS-InternVL extension | Experimental |

Do not build seven models. Build a stable primary route, then add specialists only when a measured gap justifies them.

## Core user story

> As an analyst, I upload compatible satellite observations and ask a question in natural language. SatQuery validates the assets, explains the selected task/model, performs analysis, highlights supporting evidence, states uncertainty and limitations, and produces a reproducible report.

## Product principles

1. **Evidence before spectacle.** The viewer and evidence layer are more important than decorative visuals.
2. **Explain the route.** Users can see detected modality, task, selected model, and trace.
3. **Reject incompatible work clearly.** A useful validation error is better than a plausible hallucination.
4. **Confidence must have a method.** Never manufacture precision.
5. **Progressive complexity.** Default flow is simple; band/metadata/model detail remains available.
6. **Research honesty.** Distinguish planned, mocked, inferred, and measured capabilities.
7. **Accessible motion.** Motion explains sensor fusion and never blocks analysis.

## Current architecture decisions

| Topic | Decision | Rationale |
|---|---|---|
| Primary model | RS-InternVL-style S1/S2 model | Direct research alignment with paired SAR/multispectral understanding |
| Temporal work | Separate specialist route | BigEarthNet.txt is not a temporal-change training source |
| Frontend | Next.js App Router + TypeScript | Strong application routing, server/client boundaries, ecosystem |
| UI | Tailwind + shadcn/Radix + Lucide | Tokenized, accessible, consistent controls/icons |
| Geospatial viewer | OpenLayers | Raster/EO and projection-oriented web mapping |
| Landing motion | Native MP4 + GSAP ScrollTrigger | The supplied continuous orbital-descent film is scrubbed by normal page scroll; a Next Image poster provides loading and reduced-motion fallback |
| Backend | FastAPI + Pydantic | Python/model ecosystem and typed OpenAPI contracts |
| No-GPU analysis | Query-gated deterministic EO engine | Water/flood and vegetation/green-land requests use distinct spectral/SAR methods; every other semantic request is rejected until a VLM is active |
| Model integration | Replaceable adapter protocol | Lets mock and verified inference share one product workflow |
| Routing | Deterministic compatibility rules first | Auditable behavior and fewer hallucinated selections |
| Persistence | Local dev first; Postgres/PostGIS + object storage later | Avoid infrastructure blocking model/UI proof |

## UI design context

UI/UX Pro Max was used to establish the following direction:

- Product pattern: real-time/operations interface with truthful freshness/status labels.
- Style: modern scientific soft-depth surfaces with strong contrast, not heavy neumorphism.
- Density: standard-to-dense in the workspace, spacious on the landing story.
- Motion: complex only in one purposeful narrative scene; subtle elsewhere.
- Type: Inter, with tabular figures for measurements.
- Accessibility: visible focus, keyboard support, 4.5:1 text contrast, reactive reduced-motion behavior.

### Motion concept

A single continuous photographic video moves from a front orbital satellite view, over the sensor platform, toward Earth, and into a nadir land-and-water observation. GSAP maps the user’s normal page-scroll progress to the video timeline while a queued-seek controller prevents rapid scroll updates from dropping the final requested frame. The section remains pinned until the observation frame completes. A static, eagerly loaded opening frame covers media loading and is the permanent reduced-motion fallback. The analysis workspace does not run decorative motion.

### Avoid

- Generic neon “AI space” styling that competes with imagery.
- Emoji as interface icons.
- Endless auto-rotation, scroll hijacking, excessive parallax, or multiple pinned sections.
- Glass surfaces behind dense text without tested contrast.
- Color-only legends, tiny controls, hover-only behavior, and hidden focus rings.

## System workflow

```text
Upload assets
  → inspect format/metadata/bands
  → detect or confirm modality
  → validate spatial and model compatibility
  → classify query task
  → select compatible capability from registry
  → preprocess with full provenance
  → run adapter
  → normalize and validate result
  → show answer + evidence + uncertainty + trace
  → export reproducible report
```

## Initial model registry intent

| Model ID | Inputs | Tasks | Temporal | State |
|---|---|---|---:|---|
| `rs-internvl-s1-s2` | S1 + S2 | VQA, caption; grounding if verified | No | Primary/unverified artifact |
| `geochat-rgb` | RGB | VQA, caption, grounding | No | Candidate/deferred |
| `teochat-temporal` | Optical T1…Tn | temporal QA/change | Yes | Candidate/deferred |
| `changechat-bitemporal` | Optical T1 + T2 | change QA/caption/localization | Yes | Candidate/deferred |
| `earthdial-unified` | RGB/SAR/MS/temporal variants | broad VQA/reasoning | Varies | Experimental/deferred |

## Known unknowns

Resolve these before real model implementation:

- Exact RS-InternVL public source/checkpoint and immutable revision.
- Checkpoint license and redistribution rules.
- Model parameter count and practical GPU requirements.
- Exact input band set/order, resolutions, normalization, and tiling.
- Whether single S1 and single S2 paths are supported independently.
- Grounding output representation and available evaluation scripts.
- Prompt template/tokenizer requirements.
- Confidence/log-probability access and calibration approach.
- SIH deployment machine, GPU, network, and offline constraints.
- Representative user data formats and maximum raster sizes.

## Definition of evidence-grounded output

Every completed run should contain:

- Direct answer or caption.
- Spatial evidence (bbox/mask/region) when the model genuinely supports it; otherwise an explicit limitation.
- Source asset references and preprocessing provenance.
- Selected model ID/version and routing reason.
- Confidence/score with method and calibration status, if available.
- Warnings, missing information, and compatibility notes.
- Ordered execution trace with timing.
- Reproducible downloadable report payload.

## Evaluation baseline

- VQA: accuracy, precision, recall, F1.
- MCQ: accuracy.
- Captioning: BLEU-4, METEOR, ROUGE-L, CIDEr plus domain review.
- Grounding: mIoU and thresholded accuracy.
- Agent/system: task classification, routing accuracy, incompatibility rejection, trace completeness, latency, memory, and failure recovery.

Reported BigEarthNet.txt/RS-InternVL values in research notes are background evidence, not SatQuery results. SatQuery numbers must come from a reproducible evaluation run.

## Repository conventions once scaffolded

Proposed structure:

```text
apps/
  web/
  api/
services/
  model-worker/
packages/
  contracts/
  config/
docs/
  PROJECT_CONTEXT.md
```

- Keep page-specific components beside their Next.js routes.
- Keep schemas generated from one authoritative contract path.
- Never commit model weights, secrets, uploads, or generated reports.
- Use semantic design tokens rather than raw colors inside components.
- Add a decision here whenever scope, routing, model capability, or deployment assumptions change.

## Immediate next action

Verify the RS-InternVL release and the target hardware. Then scaffold the repository, install pinned dependencies, create shared contracts, and build the mock end-to-end route before connecting real inference.
