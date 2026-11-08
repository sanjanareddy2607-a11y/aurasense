# AuraSense

**Beyond the pulse. Understand the pattern.**

AuraSense is a working AI-assisted physiological pattern research platform. It analyses
ECG, electrodermal activity, respiration, temperature and movement, runs a trained model
on WESAD-derived features, and presents estimates with signal quality, uncertainty and
feature-level explanations.

It is a research prototype, **not a medical device**. It does not diagnose stress, anxiety
or any other condition, and its outputs are not clinically validated. Throughout the UI and
reports, estimates are described as *stress-associated physiological patterns*.

---

## Problem statement

Stress and affect research often stops at offline notebooks: a model is trained, a table is
produced, and there is no usable system for inspecting an individual estimate, understanding
which physiological features drove it, comparing it with a personal baseline, or reviewing
model behaviour as a whole. At the same time, demonstrating such work responsibly requires
more than a prediction: it needs provenance, signal-quality checks, role boundaries, consent
controls and explicit warnings about what the numbers do **not** mean.

AuraSense addresses that gap as a complete, inspectable research platform rather than a
single classifier demo.

## Objectives

1. Extract interpretable cardiac, electrodermal, respiratory, temperature and movement
   features from WESAD recordings using a reproducible pipeline.
2. Train and compare three scikit-learn classifiers with **participant-grouped** evaluation,
   so no participant appears in both training and test data in a fold.
3. Expose genuine model inference through a typed API, with probability estimates, signal
   quality, uncertainty and feature-level explanations.
4. Support individual, researcher and institution roles with appropriate access boundaries.
5. Provide a usable research workflow: analysis, personal baseline, CSV laboratory, research
   metrics, consent-only aggregates and downloadable PDF reports.
6. Be explicit about simulation, dataset limitations and the absence of clinical validation.

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS v4, Recharts, React Router |
| Backend | Python 3.14, FastAPI, Uvicorn, Pydantic, SQLAlchemy |
| Machine learning | scikit-learn, NumPy, pandas, SciPy, joblib |
| Persistence | SQLite by default; PostgreSQL DSN supported by configuration |
| Reporting | fpdf2, server-side PDF generation |
| Authentication | PBKDF2-HMAC-SHA256 passwords, HS256 bearer JWTs |
| Deployment | Vercel static frontend, Render Python web service with a persistent disk |

---

## What is real

- **Dataset:** public WESAD (Wearable Stress and Affect Detection), 15 participants, chest
  and wrist sensors, neutral / stress (TSST) / amusement conditions. Preprocessing reads the
  local pickles and extracts **1,032 analysable 60-second windows** (30-second stride,
  labels neutral/stress/amusement only, ≥90% label coverage).
- **Features:** 20 interpretable features per window (cardiac, electrodermal, respiratory,
  temperature, muscle/movement). The same extraction code serves WESAD, CSV uploads and the
  simulation.
- **Models:** Random Forest, Support Vector Machine and Gradient Boosting (scikit-learn).
  XGBoost is not installed in this environment, so `HistGradientBoostingClassifier` is used
  and labelled "Gradient Boosting"; this is documented in the UI.
- **Evaluation:** 5-fold **GroupKFold by participant** — no participant appears in both
  training and test in a fold.
- **Explanations:** SHAP is not installed, so local contributions use model-agnostic
  occlusion (replace a feature with its training median and measure the probability change)
  and global importance uses permutation importance. Both are labelled accordingly.
- **Live Monitor:** synthetic chest/wrist signals generated server-side, clearly labelled as
  simulation, passed through the same preprocessing and inference path as real uploads.
- **PDF reports:** generated server-side with fpdf2 from stored analyses and the genuine
  evaluation output.

### Actual evaluation results (this installation)

| Model | Accuracy | Balanced accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| Random Forest | 82.4% | 69.7% | 70.0% |
| Support Vector Machine | 65.9% | 69.4% | 64.2% |
| **Gradient Boosting** (selected) | **82.8%** | **76.9%** | **76.7%** |

Model version: `aura-wesad-20261107-444b41`. These are laboratory, three-class results on a
small dataset, not clinical accuracy.

---

## Architecture

```
app/
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI app, CORS, startup seeding
│   │   ├── config.py          env-driven settings
│   │   ├── db.py              SQLAlchemy engine/session
│   │   ├── models.py          users, profiles, sessions, analyses, baselines,
│   │   │                      datasets, experiments, reports, signal assets
│   │   ├── schemas.py         Pydantic request models
│   │   ├── security.py        PBKDF2-HMAC-SHA256 + JWT (HS256)
│   │   ├── deps.py            auth dependencies and role checks
│   │   ├── seed.py            labelled demonstration data
│   │   ├── routers/           auth, sessions, analysis, datasets, baseline,
│   │   │                      research, reports, institution, system
│   │   └── services/          simulation, inference, analysis, baseline,
│   │                          aggregate, live, reporting, research, serializers
│   ├── ml/
│   │   ├── features.py        channel mapping, windows, 20 features, quality
│   │   ├── wesad_extract.py   pickle → cached window features
│   │   ├── train.py           grouped CV, metrics, model persistence
│   │   └── artifacts/         model.joblib, metrics.json, feature cache
│   └── tests/                 pipeline, inference, persistence, metrics
├── frontend/                  React + TypeScript + Vite + Tailwind v4 + Recharts
│   └── src/pages/             Landing, Login/Register, Overview, Live Monitor,
│                              AI Analysis, My Baseline, BioSignal Lab,
│                              Research Centre, Institution Insights,
│                              Reports & History, Settings
├── .env.example
└── README.md
```

Local WESAD data lives at `BIO-EXP-PROJECT/WESAD/S2..S17` and is never committed or copied
into the app.

---

## Quick start (Windows)

### 1. Backend

```bash
cd app/backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Create `app/.env` from `app/.env.example` (optional for local defaults).

### 2. Extract WESAD features and train (only needed once)

```bash
cd app/backend
.venv/Scripts/python.exe -m ml.wesad_extract     # ~15–25 min, writes cached CSVs
.venv/Scripts/python.exe -m ml.train             # grouped CV + model.joblib
```

The app still starts with a missing model, but analyses are disabled and the Research Centre
shows a setup notice. `ml/artifacts/` is already populated in this workspace.

### 3. Seed and run the API

```bash
cd app/backend
.venv/Scripts/python.exe -m app.seed             # idempotent; add --reset to rebuild
.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Interactive API docs: <http://127.0.0.1:8010/docs>

> Port 8010 is used because port 8000 was already occupied on this machine. The Vite proxy is
> configured to match.

### 4. Frontend

```bash
cd app/frontend
npm install
npm run dev
```

Open <http://127.0.0.1:5173>. The dev server proxies `/api` to `http://127.0.0.1:8010`.

Production build: `npm run build` (TypeScript + Vite).

---

## Deployment

AuraSense is a two-service deployment:

```
Browser
  │
  ├── Vercel static site ── React/Vite build (frontend/dist)
  │        │
  │        └── HTTPS + CORS ── Render Python web service
  │                                  ├── FastAPI /api
  │                                  ├── trained model + cached features
  │                                  └── /var/data persistent disk
  │                                        ├── aurasense.db
  │                                        └── storage/ (uploads, PDFs)
  └── public HTTPS URL
```

**Why not the backend on Vercel?** The API is not a stateless function. It keeps a SQLite
database, writes uploaded CSVs and generated PDFs to local storage, and loads a scikit-learn
model from disk. Vercel's serverless filesystem is ephemeral, so those records would disappear
between invocations. Vercel hosts the static frontend; Render hosts the long-running API with
a persistent disk.

The repository includes `render.yaml` for the backend and `frontend/vercel.json` for the SPA
rewrite. No application source changes are needed for this architecture.

### Backend: Render

| Setting | Value |
| --- | --- |
| Runtime | Python 3.14 |
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/api/health` |
| Plan | Starter or higher (a persistent disk requires a paid instance) |
| Disk | 1 GB at `/var/data` |

Required environment variables:

```text
SECRET_KEY=<long random value>
AURASENSE_ENV=production
DATABASE_URL=sqlite:////var/data/aurasense.db
DATA_DIR=/var/data
STORAGE_DIR=/var/data/storage
CORS_ORIGINS=https://<frontend-domain>
SEED_DEMO=1
RESEARCH_INVITE_CODE=<private code>
DEMO_INDIVIDUAL_PASSWORD=<private password>
DEMO_RESEARCHER_PASSWORD=<private password>
DEMO_ADMIN_PASSWORD=<private password>
DEMO_COHORT_PASSWORD=<private password>
MAX_UPLOAD_BYTES=12582912
INSTITUTION_MIN_COHORT=5
```

The raw WESAD dataset is **not** deployed. Reference inference and research experiments use
`backend/ml/artifacts/wesad_features.csv`, which is committed with the model and metrics.

### Frontend: Vercel

| Setting | Value |
| --- | --- |
| Root directory | `frontend` |
| Build command | `npm ci && npm run build` |
| Output directory | `dist` |
| Environment variable | `VITE_API_URL=https://<backend-domain>/api` |
| Routing | Rewrite all paths to `/index.html` for React Router |

`VITE_API_URL` is compiled into the bundle, so changing it requires a new frontend build.
After the frontend URL is known, set the backend's `CORS_ORIGINS` to that exact origin and
redeploy the backend.

### Updating a deployment

1. Change the source locally and run the backend tests and `npm run build`.
2. Commit and push to the `main` branch.
3. Render redeploys the backend automatically; Vercel redeploys the frontend automatically.
4. If an environment variable changed, redeploy the affected service. The SQLite database and
   stored reports remain on the Render disk across normal deploys.

Do not run multiple backend instances or multiple Uvicorn workers against the same SQLite
database. For a multi-instance public deployment, migrate the data layer to PostgreSQL and
an object store first, and test that migration explicitly.

---

## Demonstration accounts

| Role | Email | Local password | Access |
| --- | --- | --- | --- |
| Individual | `demo@aurasense.app` | `Demo1234!` | Own analyses, baseline, lab, reports |
| Researcher | `researcher@aurasense.app` | `Research1234!` | + Research experiments, aggregates, research PDFs |
| Institution | `institution@aurasense.app` | `Institution1234!` | + Institution aggregate view and reports |

The passwords above are the **local development defaults**. A production deployment should
set `DEMO_INDIVIDUAL_PASSWORD`, `DEMO_RESEARCHER_PASSWORD`, `DEMO_ADMIN_PASSWORD` and
`DEMO_COHORT_PASSWORD` to private values before the first seed. The seeded institution
account has the `admin` role, so its password must never be left at the public default.

Researcher self-registration requires the code `AURA-RESEARCH` (configurable via
`RESEARCH_INVITE_CODE`).

All seeded users, sessions and analyses are marked **demo** in the API and UI. The demo
cohort (12 synthetic participants) has explicitly opted into aggregate sharing.

---

## Features by module

The eight core modules are Overview, Live Monitor, AI Analysis, My Baseline, BioSignal Lab,
Research Centre, Institution Insights and Reports & History. Landing and Settings are
supporting screens.

- **Landing** — editorial product page with the real balanced-accuracy figure fetched from the
  API, science and privacy sections.
- **Overview** — latest estimate, quality, baseline maturity, probability history, recent
  analyses and model card.
- **Live Monitor** — five labelled scenarios (resting, arousal, recovery, activity, noisy),
  live ECG/EDA/respiration/motion waveforms, beat-to-beat heart-rate trend, quality state,
  prediction history. Pause/resume/finish; finishing stores a full analysis.
- **AI Analysis** — run inference on a cached WESAD window (participant/condition selectable)
  or a demonstration dataset; view probabilities, uncertainty, occlusion contributions,
  global importance, extracted features, imputed features and provenance.
- **My Baseline** — personal feature means ± SD, reliability tier, trend, contrast with the
  latest analysis (z-scores), recalculation and reset.
- **BioSignal Lab** — CSV/TSV upload with automatic channel and sampling-rate detection,
  data inspection, channel previews, quality report and analysis.
- **Research Centre** — dataset summary, model comparison, confusion matrices, per-class and
  per-participant results, permutation importance, reproducible grouped-CV experiments and a
  research PDF.
- **Institution Insights** — consent-only aggregates, weekly composition, cohort suppression,
  CSV export and aggregate PDF. Individuals are blocked with an explanatory page.
- **Reports & History** — generate, download and delete PDFs; source links to analyses.
- **Settings** — profile, sharing and raw-signal retention toggles, baseline preference,
  password change, JSON export, account deletion.

---

## Signal quality and uncertainty

Quality is scored 0–100 from duration, missing channels/gaps, flat channels, high-frequency
noise, implausible heart rate or beat-to-beat irregularity, and out-of-range EDA/temperature.
`good ≥ 80`, `fair ≥ 60`, `poor ≥ 40`, otherwise `insufficient`. Poor quality surfaces explicit
issues and lowers confidence; low-quality readings are never silently presented as reliable.

CSV ingestion recognises aliases such as `ECG/EKG`, `EDA/GSR/SC`, `Resp/RSP`, `Temp`,
`EMG`, `ACC_x/y/z`, `BVP/PPG`, `HR`, and time columns including `time`, `timestamp`,
`t`, `time_s`, `seconds`, `elapsed`. Sampling rate is read from a time column when possible,
otherwise from the optional upload field, then defaults to 64 Hz with a visible warning.

---

## Tests

```bash
cd app/backend
.venv/Scripts/python.exe -m pytest tests -q
```

Verified result in this environment: **5 passed** — time-column sampling detection, noisy
signal quality flagging, resting-scenario prediction with normalised probabilities, grouped
evaluation integrity (1,032 windows, 15 participants, best balanced accuracy in a realistic
range), and persistence with model provenance and local explanations.

Additional manual/API verification performed:

- login for all three roles; individual blocked from institution aggregates (403)
- live session ticks → stress-associated estimate → finish → stored analysis
- CSV upload (48 s, 250 Hz) → 1 window, 250 Hz detected from `time_s`, neutral estimate
- WESAD reference inference → analysis created
- analysis PDF (4.4 KB), research PDF (6.0 KB), institution PDF (2.0 KB), aggregate CSV
- frontend production build (`tsc -b && vite build`) passes
- browser smoke test: landing, sign-in, overview, research centre, institution insights

---

## Future scope

- External identity, email verification and password reset.
- PostgreSQL plus object storage for horizontal scaling.
- Calibrated probabilities and a prospective, external validation cohort.
- Wearable-device ingestion; Live Monitor today is explicitly a simulation.
- Richer consent management and auditable data-retention controls.
- Clinical validation and regulatory review before any diagnostic claim.

---

## Known limitations

- WESAD is small (15 participants), laboratory-based and not demographically diverse.
  Results do not establish generalisation to daily life or to any individual.
- Amusement is the smallest class and is frequently confused with neutral; stress recall is
  higher than precision.
- The chest/wrist sensor configuration differs from consumer wearables. Uploaded CSVs are
  assumed to represent comparable channels.
- Skin-conductance tonic/phasic separation uses a moving-average estimate, not full
  deconvolution.
- Occlusion contributions and permutation importance describe model behaviour, not causation.
- Simulation scenarios are illustrative and can be classified imperfectly (for example,
  "activity" and "noisy" often resemble neutral with reduced quality). They are never
  presented as measurements of a person.
- SQLite by default; PostgreSQL is supported through `DATABASE_URL` but was not exercised here.
- No email verification, password reset or external identity provider is included.
- PDFs use a built-in font: extended Unicode (e.g. some symbols) may be transliterated.

---

## Data, privacy and research ethics

- Aggregate institution views only include users with `share_aggregate = true`.
- Groups require at least 5 sessions and 3 participants (configurable); smaller groups are
  suppressed and counted, never partially shown.
- Individuals cannot access institution aggregates.
- Users can export their data as JSON and delete their account and associated records.
- Raw simulated signal retention is optional (`store_raw_signals`).
- No diagnosis, triage, surveillance, ranking or performance assessment is supported.

**Citation:** Schmidt, P., & Reiss, A. (2018). *WESAD (Wearable Stress and Affect Detection).*
UCI Machine Learning Repository. DOI: [10.24432/C57K5T](https://doi.org/10.24432/C57K5T)

---

## API overview

| Area | Endpoints |
| --- | --- |
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`, `PATCH /api/auth/profile`, `POST /api/auth/password`, `DELETE /api/auth/account`, `GET /api/auth/export` |
| Monitoring | `GET /api/sessions/scenarios`, `POST /api/sessions`, `POST /api/sessions/{id}/tick`, `pause`, `resume`, `stop`, `DELETE /api/sessions/{id}` |
| Analysis | `POST /api/analysis/upload`, `POST /api/analysis/reference`, `POST /api/analysis/demo`, `GET /api/analysis`, `GET/DELETE /api/analysis/{id}` |
| Datasets | `GET /api/datasets`, `GET /api/datasets/{id}`, `GET /api/datasets/{id}/preview` |
| Baseline | `GET /api/baseline`, `POST /api/baseline/recalibrate`, `POST /api/baseline/reset` |
| Research | `GET /api/research/overview`, `GET /api/research/metrics`, `POST /api/research/experiments` |
| Reports | `POST /api/reports/analysis/{id}`, `POST /api/reports/research`, `POST /api/reports/institution`, `GET /api/reports/{id}/download`, `DELETE /api/reports/{id}` |
| Institution | `GET /api/institution/overview`, `GET /api/institution/export` (researcher/admin only) |
| System | `GET /api/health`, `GET /api/model/info`, `GET /api/meta` |

Authentication uses a bearer JWT; passwords are hashed with PBKDF2-HMAC-SHA256 (260,000
iterations). Set a strong `SECRET_KEY` before sharing the API.
