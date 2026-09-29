# SatQuery AI 🛰️

[![CI](https://github.com/asadullah098/SatQuery-AI/actions/workflows/ci.yml/badge.svg)](https://github.com/asadullah098/SatQuery-AI/actions/workflows/ci.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9+-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

> **Verifiable, query-driven Earth Observation intelligence fusing Sentinel-1 SAR and Sentinel-2 multispectral imagery via transparent multimodal vision-language models.**

Developed for the **Smart India Hackathon (SIH)**, **SatQuery AI** transforms raw multi-sensor satellite imagery into actionable, natural-language geospatial intelligence. Instead of treating remote sensing as a black-box problem, SatQuery AI pairs multimodal Vision-Language Models (RS-InternVL) with a deterministic, auditable controller that validates inputs, detects modalities, traces execution steps, and quantifies uncertainty.

---

## 🌟 Key Features

- **Co-Registered Multi-Sensor Fusion**: Seamlessly aligns and jointly analyzes Sentinel-1 Synthetic Aperture Radar (SAR) and Sentinel-2 multispectral (MS) observations.
- **Natural Language VQA & Captioning**: Ask questions directly in natural language (e.g., *"Assess flood extent in the agricultural sectors"* or *"Identify vegetation health indices"*).
- **Dual Inference Pipeline**:
  - **Multimodal VLM Route (RS-InternVL)**: Remote specialist route for joint cross-sensor reasoning, detailed captions, and grounding.
  - **Deterministic EO Engine (CPU/Edge)**: Fast, exact spectral index computation (NDVI for vegetation, NDWI / SAR backscatter thresholding for water bodies and flood detection) without requiring GPU resources.
- **Transparent Execution & Auditability**: Every run produces an ordered, timed trace, input compatibility reports, calibrated confidence estimates, and downloadable verification artifacts (PDF & JSON).
- **Interactive Geospatial Workspace**:
  - Side-by-side interactive swipe comparison between SAR and multispectral bands.
  - Real-time SSE (Server-Sent Events) analysis logs and execution milestones.
  - Comprehensive run history (`/runs`) and model capability registry (`/models`).
- **Cinematic Orbital Telemetry**: Immersive scroll-scrubbed orbital entry narrative built with GSAP and Three.js / React Three Fiber.

---

## 🏗️ Architecture & Monorepo Layout

```text
SatQuery-AI/
├── apps/
│   ├── api/                   # FastAPI backend service
│   │   ├── satquery_api/      # Asset validation, preprocessing, adapters & storage
│   │   │   ├── adapters.py    # Model worker adapter interface (mock & remote GPU)
│   │   │   ├── assets.py      # GeoTIFF raster inspection & preview generation
│   │   │   ├── deterministic.py # NDVI, NDWI & SAR flood analysis algorithms
│   │   │   ├── preprocessing.py # Multi-sensor spatial alignment & reprojection
│   │   │   └── storage.py     # Local SQLite persistence engine
│   │   ├── tests/             # Pytest test suite
│   │   └── Dockerfile
│   └── web/                   # Next.js 15 App Router web application
│       ├── src/
│       │   ├── app/           # App router pages (workspace, models, runs)
│       │   └── components/    # Interactive viewers, film timeline & UI tokens
│       └── Dockerfile
├── packages/
│   └── contracts/             # Shared TypeScript schemas, types & API interfaces
├── docs/                      # Architectural context and scientific specifications
├── .github/workflows/         # Automated GitHub Actions CI pipeline
├── docker-compose.yml         # Containerized local deployment
├── pnpm-workspace.yaml        # Monorepo workspace configuration
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Node.js**: `v20+` or `v22+` (with `corepack` or `pnpm` installed)
- **Python**: `3.11+` or `3.12+`
- **GDAL / Rasterio compatible libraries** (included in standard pip wheels)
- *(Optional)* **Docker & Docker Compose**

---

### Method 1: Local Development

#### 1. Clone the repository

```bash
git clone https://github.com/asadullah098/SatQuery-AI.git
cd SatQuery-AI
```

#### 2. Configure Environment

Copy the example environment configuration:

```bash
cp .env.example .env
```

#### 3. Setup and Run the Backend API

```powershell
# Navigate or stay at project root
python -m venv .venv
.\.venv\Scripts\Activate.ps1    # On Linux/macOS: source .venv/bin/activate

# Install backend dependencies
pip install -e "apps/api[dev]"

# Start FastAPI development server
python -m uvicorn satquery_api.main:app --app-dir apps/api --reload --port 8000
```

The API will be live at `http://localhost:8000`. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

#### 4. Setup and Run the Frontend

In a separate terminal window:

```bash
# Enable pnpm via corepack if not globally installed
corepack enable
pnpm install

# Start the Next.js development server
pnpm dev
```

Open `http://localhost:3000` in your browser.
- **Interactive Workspace**: `http://localhost:3000/workspace`
- **Run History & PDF Reports**: `http://localhost:3000/runs`
- **Model Registry**: `http://localhost:3000/models`

---

### Method 2: Docker Compose

Spin up both the web frontend and API services simultaneously:

```bash
docker compose up --build
```

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`

---

## 🧪 Verification & Testing

SatQuery AI includes automated CI tests verifying type safety, linting standards, and backend endpoints:

```powershell
# Typecheck TypeScript codebase
pnpm typecheck

# Lint frontend code
pnpm lint

# Build web frontend
pnpm build

# Lint Python code with Ruff
python -m ruff check apps/api

# Run backend unit tests with Pytest
python -m pytest apps/api/tests -q
```

---

## 🛰️ Sensor Specifications & Supported Modalities

| Modality | Sensor Platform | Native Bands / Polarizations | Primary Analysis Tasks |
|---|---|---|---|
| **SAR** | Sentinel-1 | VV, VH (Interferometric Wide Swath) | Flood mapping, surface roughness, all-weather monitoring |
| **Multispectral** | Sentinel-2 | B2 (Blue), B3 (Green), B4 (Red), B8 (NIR) | Land cover, crop monitoring, NDVI vegetation indexing |
| **Fused Joint** | Sentinel-1 + Sentinel-2 | Co-registered SAR backscatter + Multispectral bands | Deep multimodal VQA, cross-sensor anomaly detection, captioning |

---

## ⚙️ Inference Modes

SatQuery AI supports flexible runtime configurations controlled via environment variables:

- **`deterministic` (Default)**: Executes fast, exact rule-based EO scientific calculations (NDVI, NDWI, SAR polarimetric thresholding) on CPU without GPU overhead.
- **`mock`**: Simulates RS-InternVL multimodal VLM responses with full execution tracing and telemetry for offline UI testing and demonstration.
- **`remote`**: Connects to a high-capacity GPU model worker hosting `RS-InternVL` checkpoints via `SATQUERY_MODEL_WORKER_URL`.

---

## 🤝 Contributing

Contributions, feedback, and issue submissions are welcome!

1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
