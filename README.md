# ARGUS — Adaptive Regulatory Graph for Unseen Surveillance

> **Enterprise-Grade AI System for Real-Time Indian Market Manipulation Detection**  
> Built for SEBI, NSE, BSE regulatory teams and compliance departments.

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3.0-orange)](https://pytorch.org)
[![License](https://img.shields.io/badge/License-Proprietary-red)](#)
[![Status](https://img.shields.io/badge/Status-Operational%20✅-brightgreen)](#current-status)

---

## Table of Contents

1. [What is ARGUS?](#what-is-argus)
2. [System Architecture](#system-architecture)
3. [AI Engines](#ai-engines)
4. [Detection Capabilities](#detection-capabilities)
5. [Scoring Formula](#scoring-formula)
6. [Project Structure — Every File Explained](#project-structure--every-file-explained)
   - [Root Files](#root-level-files)
   - [API Layer (`api/`)](#api-layer-api)
   - [AI Models (`models/`)](#ai-models-models)
   - [Data Layer (`data/`)](#data-layer-data)
   - [Scoring Engine (`scoring/`)](#scoring-engine-scoring)
   - [Streamlit Dashboard (`dashboard/`)](#streamlit-dashboard-dashboard)
   - [React Dashboard (`argus-dashboard/`)](#react-dashboard-argus-dashboard)
   - [Reports (`reports/`)](#reports-reports)
   - [Database Migrations (`alembic/`)](#database-migrations-alembic)
   - [Tests (`tests/`)](#tests-tests)
   - [Demo (`demo/`)](#demo-demo)
7. [Database Schema](#database-schema)
8. [Data Sources](#data-sources)
9. [API Reference](#api-reference)
10. [Quick Start — Local Dev](#quick-start--local-dev)
11. [Docker Deployment](#docker-deployment)
12. [Current Status](#current-status)
13. [Known Limitations](#known-limitations)
14. [Roadmap](#roadmap)

---

## What is ARGUS?

ARGUS (**A**daptive **R**egulatory **G**raph for **U**nseen **S**urveillance) is an enterprise AI system that monitors Indian capital markets in real-time and automatically detects market manipulation schemes before or as they happen.

It combines **4 independent AI engines** — graph neural networks, behavioral biometrics, cross-market fusion, and zero-day anomaly detection — into a single weighted score that triggers alerts for SEBI enforcement action.

**Core purpose:**
- Detect pump & dump, spoofing, layering, circular trading, and insider trading signals
- Generate SEBI-compliant case reports with evidence automatically
- Provide a real-time surveillance dashboard for market regulators
- Build behavioral DNA fingerprints of traders to identify repeat offenders

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                                │
│  NSE Bhavcopy  │  BSE Announcements  │  SEBI Orders  │  MCA21      │
│  NSE Bulk Deals│  Broker Feed (Kite) │  Kafka Stream │  MCX Data   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │  ETL PIPELINE   │
                    │  data/ingest/   │
                    │  data/pipeline/ │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
  ┌───────▼──────┐  ┌────────▼──────┐  ┌───────▼──────┐  ┌──────────────┐
  │  GNN / TCN   │  │ DNA Autoencdr │  │ Cross-Market │  │  Zero-Day    │
  │ models/gnn/  │  │ models/dna/   │  │ models/cross │  │ models/zero  │
  │ [TRAINED ✅] │  │ [TRAINED ✅]  │  │ _market/     │  │ _day/        │
  └───────┬──────┘  └────────┬──────┘  └───────┬──────┘  └──────┬───────┘
          │                  │                  │                │
          └──────────────────┼──────────────────┘                │
                             │                                   │
                    ┌────────▼────────────────────────────────────┐
                    │            SCORING ENGINE                    │
                    │  scoring/alert_engine.py                     │
                    │  scoring/impossibility.py                    │
                    │  Score = 0.35×GNN + 0.25×ZeroDay +          │
                    │          0.25×DNA + 0.15×CrossMarket         │
                    └────────┬────────────────────────────────────┘
                             │
               ┌─────────────┼──────────────────┐
               │             │                  │
      ┌────────▼────────┐    │         ┌────────▼────────┐
      │   FastAPI API   │    │         │  React/Vite UI  │
      │   api/main.py   │    │         │ argus-dashboard/│
      │   Port 8080     │    │         │   Port 5173     │
      └────────┬────────┘    │         └─────────────────┘
               │     ┌───────▼──────────┐
      ┌────────▼────┐│ Streamlit UI     │
      │  PDF Reports││ dashboard/app.py │
      │reports/pdf_ ││ Port 8501        │
      │generator.py ││                  │
      └─────────────┘└──────────────────┘
```

---

## AI Engines

### 1. Temporal Coincidence Network (GNN)
**Weight: 35% of total score**

A **Graph Attention Network (GAT)** that models trading activity as a dynamic graph. Each account is a node; edges form when two accounts trade the same scrip within a configurable time window (default: 50ms). The GNN learns to detect coordinated patterns — multiple accounts acting in suspicious synchrony — that indicate layering, spoofing, or circular trading rings.

**How it works:**
- Highly optimized, vectorized graph construction (eliminates O(n²) bottlenecks).
- Uses a **max-node-degree Poisson null model** to detect structural anomalies and impossible coincidence densities.
- Builds a PyTorch Geometric `Data` object from trade records.
- 3-layer GAT with edge-conditioned attention outputting per-node manipulation probability [0, 1].

**Training:** Trained on 50 manipulated + 50 normal synthetic graphs for 30 epochs using Adam + StepLR scheduler with gradient clipping (max norm 1.0). Weights saved to `models/gnn/tcn_weights.pt` (345 KB). Best checkpoint selected by AUC-ROC on held-out validation set.

### 2. Behavioral DNA Autoencoder
**Weight: 25% of total score**

An **LSTM-based autoencoder** that compresses each account's trading behavior into a 32-dimensional "DNA vector". This fingerprint captures unique behavioral patterns: typical trade size, timing habits, preferred instruments, order-to-trade ratio, etc.

**How it works:**
- Extracts 32 features per account from their trade history
- Encodes to 32-dim latent vector (the DNA fingerprint)
- High reconstruction error = anomalous/unusual behavior
- Cosine similarity matching against a database of **known fraudster DNA vectors**
- Similarity > 0.85 flags the account as a potential repeat offender

**Training:** Trained on synthetic normal and anomalous trade sequences. Weights saved to `models/dna/autoencoder_weights.pt` (341 KB). Run `models/dna/train_on_synthetic.py` to retrain.

### 3. Cross-Market Phantom Detector
**Weight: 15% of total score**

Detects **derivative-spot manipulation** by fusing signals across NSE equity, NSE F&O, BSE, and MCX simultaneously. A trader who manipulates spot prices to profit on futures — or who creates artificial activity in one market to influence another — leaves cross-market footprints this engine catches.

**How it works:**
- Computes cross-market correlation matrices
- Detects lead-lag relationships between spot and derivative activity
- DoWhy causal inference to distinguish causation from correlation
- Flags when a single entity's activity spans multiple markets simultaneously

### 4. Zero-Day Anomaly Ensemble
**Weight: 25% of total score**

A **4-model ensemble** for detecting novel manipulation schemes that have never been seen before and therefore cannot be caught by rule-based or supervised systems.

**Ensemble members:**
- `IsolationForest` — partition-based outlier detection
- `LocalOutlierFactor` — density-based local anomaly scoring
- `HBOS` (Histogram-Based Outlier Score) — fast univariate outlier detector
- `OCSVM` (One-Class SVM) — maximum-margin novelty detector

All four scores are averaged into a single zero-day score. This engine requires no labeled fraud data and continuously adapts.

---

## Detection Capabilities

| Scheme | Primary Engine | Description |
|---|---|---|
| **Pump & Dump** | GNN + Zero-Day | Coordinated buying to inflate price, then mass sell |
| **Spoofing** | GNN | Placing large orders to move price, then cancelling |
| **Layering** | GNN | Multiple fake orders across price levels |
| **Circular Trading** | GNN + DNA | Same beneficial owner trading with themselves |
| **Insider Trading** | Zero-Day | Unusual concentrated activity before announcements |
| **Cross-Market Manipulation** | Cross-Market | Futures-spot arbitrage manipulation |
| **Wash Trading** | DNA + GNN | Artificial volume with no change in beneficial ownership |
| **Painting the Tape** | GNN | End-of-day price manipulation |
| **Front Running** | Zero-Day | Trading ahead of known large orders |
| **Churning** | DNA | Excessive trading to generate commissions |

---

## Scoring Formula

```
Overall Score (0–10) =
    0.35 × TCN/GNN Score
  + 0.25 × Zero-Day Ensemble Score
  + 0.25 × DNA Autoencoder Score
  + 0.15 × Cross-Market Fusion Score
```

**Alert Threshold:** Score ≥ **7.5** → Alert created & sent to dashboard

The `impossibility.py` module applies multiplicative boosters for statistically impossible patterns:
- Exact-same timestamp trades across unrelated accounts → ×1.8
- Order size precisely matching available liquidity → ×1.5
- Perfect price improvement sequence → ×1.6

---

## Project Structure — Every File Explained

```
argus/
├── api/                    # FastAPI backend
├── models/                 # All 4 AI engines
│   ├── gnn/                # Graph Neural Network (TCN) + trained weights
│   │   ├── tcn.py
│   │   ├── train_tcn.py
│   │   ├── train_on_synthetic.py
│   │   └── tcn_weights.pt          # ✅ Trained (345 KB)
│   ├── dna/                # Behavioral DNA Autoencoder + trained weights
│   │   ├── autoencoder.py
│   │   ├── fingerprint_store.py
│   │   ├── train_on_synthetic.py
│   │   └── autoencoder_weights.pt  # ✅ Trained (341 KB)
│   ├── cross_market/       # Cross-market fusion detector
│   └── zero_day/           # Zero-day anomaly ensemble
├── data/                   # Data ingestion & database
│   ├── db/                 # SQLAlchemy ORM models, CRUD, sessions
│   ├── ingest/             # Data fetchers (NSE, BSE, SEBI, MCA, Broker)
│   └── pipeline/           # Kafka stream processing & data cleaning
├── scoring/                # Alert engine & scoring logic
├── dashboard/              # Streamlit multi-page surveillance dashboard
│   ├── app.py              # Main entry point (Port 8501)
│   └── pages/              # Live Alerts, Account DNA, Network Graph, Case Builder
├── argus-dashboard/        # React/Vite military-grade terminal dashboard
│   └── src/
│       ├── pages/          # LiveAlerts, AccountDNA, NetworkView, CaseBuilder, WeeklySummary
│       ├── components/     # 11 reusable UI components
│       └── api/            # Axios client + mock data layer
├── reports/                # SEBI-compliant PDF case generator
├── alembic/                # Database migration scripts
├── tests/                  # Pytest test suite (4 test modules)
├── demo/                   # Demo scenarios & synthetic fraud data
│   ├── real_cases/         # 3 real-case detection scenarios
│   ├── run_demo.py
│   └── synthetic_fraud.py
├── verify_argus.py         # 10-step full system verification suite
├── .env                    # Environment variables (local dev)
├── .env.example            # Environment variable template
├── docker-compose.yml      # Full stack Docker orchestration
├── Dockerfile.api          # API + worker container
├── Dockerfile.dashboard    # React dashboard container
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic migration configuration
├── pyrightconfig.json      # VS Code Pyright type-checker config
├── pytest.ini              # Pytest configuration
└── argus_dev.db            # Auto-created SQLite DB (local dev)
```

---

## Root-Level Files

### `.env`
**Role:** Runtime environment configuration.

Contains all secrets and service URLs for local development:
```ini
POSTGRES_URL=postgresql://argus:argus@localhost:5432/argus
REDIS_URL=redis://localhost:6379
KAFKA_BOOTSTRAP=localhost:9092
NSE_ARCHIVE_BASE=https://archives.nseindia.com
BSE_ARCHIVE_BASE=https://www.bseindia.com
ZERODHA_API_KEY=your_key_here
ZERODHA_ACCESS_TOKEN=your_token_here
ALERT_SCORE_THRESHOLD=7.5
DNA_SIMILARITY_THRESHOLD=0.85
JWT_SECRET=change_me_in_production
ADMIN_PASSWORD=argus2024
```

Loaded at startup by `python-dotenv`. **Never commit to git.**

### `.env.example`
**Role:** Safe template without real secrets. Committed to git so new developers know what variables to provide.

### `requirements.txt`
**Role:** Python dependency manifest for the entire project.

Key dependencies and their purpose:
| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.111.0 | REST API framework |
| `uvicorn[standard]` | 0.29.0 | ASGI server |
| `sqlalchemy` | 2.0.30 | ORM for PostgreSQL/SQLite |
| `alembic` | 1.13.1 | Database schema migrations |
| `torch` | 2.3.0 | Deep learning (GNN + DNA models) |
| `torch-geometric` | 2.5.3 | Graph neural network library |
| `scikit-learn` | 1.4.2 | ML utilities |
| `pyod` | 1.1.3 | Outlier/anomaly detection library |
| `redis` | 5.0.4 | Caching and pub/sub |
| `kafka-python` | 2.0.2 | Real-time trade stream consumer |
| `streamlit` | 1.35.0 | Streamlit surveillance dashboard |
| `plotly` | 5.22.0 | Interactive charts |
| `reportlab` | 4.2.0 | PDF generation for SEBI cases |
| `python-jose` | 3.3.0 | JWT authentication |
| `passlib[bcrypt]` | 1.7.4 | Password hashing |
| `dowhy` | 0.11.1 | Causal inference for cross-market model |
| `networkx` | 3.3 | Graph data structures |
| `kiteconnect` | 5.0.1 | Zerodha broker API client |
| `pydantic` | 2.7.1 | Request/response schema validation |
| `psycopg2-binary` | 2.9.9 | PostgreSQL driver |
| `pyvis` | 0.3.2 | Interactive network graph rendering |
| `sse-starlette` | 2.1.0 | Server-Sent Events for live alert stream |
| `pdfplumber` | 0.11.0 | PDF scraping for SEBI enforcement orders |
| `msgpack` | 1.0.8 | Binary serialization for Kafka messages |

### `docker-compose.yml`
**Role:** Orchestrates the full production stack with 6 services:

| Service | Image | Port | Role |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Primary database |
| `redis` | redis:7-alpine | 6379 | Caching & pub/sub |
| `zookeeper` | cp-zookeeper:7.5.0 | 2181 | Kafka coordinator |
| `kafka` | cp-kafka:7.5.0 | 9092 | Trade stream message broker |
| `argus-api` | Custom (Dockerfile.api) | 8000 | FastAPI + model server |
| `argus-dashboard` | Custom (Dockerfile.dashboard) | 5173 | React UI |
| `argus-worker` | Custom (Dockerfile.api) | — | Kafka consumer worker |

All services share `argus-net` bridge network. PostgreSQL data is persisted via `postgres_data` volume.

### `Dockerfile.api`
**Role:** Container definition for the FastAPI API server and the Kafka worker. Uses Python 3.11 slim, installs requirements, and runs `uvicorn api.main:app` on port 8000.

### `Dockerfile.dashboard`
**Role:** Container definition for the React dashboard. Runs `npm run dev` on port 5173.

### `alembic.ini`
**Role:** Configuration for Alembic database migration tool. Points to the `alembic/` directory and the database URL. Used to run `alembic upgrade head` to apply schema changes without data loss.

### `pyrightconfig.json`
**Role:** Tells VS Code's Pylance/Pyright type-checker to look inside `.venv/` for installed packages, eliminating false "module not found" errors.

### `pytest.ini`
**Role:** Pytest configuration. Sets `asyncio_mode = auto` for async test support and `testpaths = tests/`.

### `argus_dev.db`
**Role:** SQLite database created automatically when running locally without PostgreSQL. Acts as a full local development database. In production, replaced by PostgreSQL. Created and managed by `data/db/session.py`.

### `verify_argus.py`
**Role:** 10-step full system verification suite. Run from project root to confirm every component is working correctly — covers DB init, trained model weights, scoring engine, PDF generation, FastAPI app, AlertEngine, and the pump-and-dump real-case detection.

```bash
python verify_argus.py
```

Expected output when fully operational:
```
========================================================
ARGUS FULL VERIFICATION SUITE
========================================================
  [PASS] SQLite DB init + table creation
  [PASS] GNN TCN model + trained weights
  [PASS] DNA Autoencoder + trained weights
  [PASS] Zero-Day Detector fit+score
  [PASS] Cross-Market Fusion import
  [PASS] Impossibility + composite scoring
  [PASS] SEBI PDF report generation
  [PASS] FastAPI app import
  [PASS] AlertEngine init (no Redis)
  [PASS] Demo: pump_and_dump run_detection()

Results: 10 PASSED  |  0 FAILED
========================================================
ARGUS is fully operational.
```

---

## API Layer (`api/`)

The API layer is a **FastAPI** application exposing all ARGUS functionality as a secured REST API with JWT authentication.

### `api/__init__.py`
Minimal package initializer. Makes `api` a Python package importable across the project.

### `api/auth.py`
**Role:** Centralized JWT authentication dependency — extracted into its own module to prevent circular imports.

**Key components:**
- `JWT_SECRET` — loaded from env; signs all tokens
- `JWT_ALGORITHM` — HS256 (HMAC-SHA256)
- `oauth2_scheme` — FastAPI OAuth2 bearer token extractor
- `get_current_user(token)` — **FastAPI dependency** used by all protected routes. Decodes and validates the JWT, returning the user payload. If the token is invalid or expired, raises HTTP 401.

**Why it was separated:** The original `api/main.py` defined `get_current_user` locally. All 3 router files imported it from `api.main`, causing a **circular import** (`main` imports routers, routers import main). Moving auth to `api/auth.py` broke this cycle.

### `api/main.py`
**Role:** FastAPI application entrypoint. Wires everything together.

**What it does:**
- Creates the `FastAPI` app with title, version, and lifespan
- Registers **CORS middleware** allowing the dashboard (e.g., at `localhost:5173`)
- Includes all 3 routers with their URL prefixes
- **Lifespan startup** (`@asynccontextmanager`): On startup, creates all DB tables (`Base.metadata.create_all`), then attempts to load all 4 AI models into `_app_state` dict. Model load failures are non-fatal (logged as warnings, model set to `None`)
- **`POST /auth/token`** — Login endpoint. Validates username/password against the admin user, returns JWT bearer token
- **`GET /health`** — System health check. Tests DB with `SELECT 1`, pings Redis, reports model load status
- **Admin user** — Single admin account (`admin` / configurable password) stored in memory for dev

### `api/schemas.py`
**Role:** All Pydantic v2 request and response models for the API.

**Schemas defined:**
| Schema | Type | Used for |
|---|---|---|
| `TokenResponse` | Response | `POST /auth/token` — returns access_token |
| `HealthOut` | Response | `GET /health` — status, services, model versions |
| `AlertOut` | Response | Alert read model with all fields |
| `AlertStatusUpdate` | Request | `POST /alerts/{id}/status` body |
| `AlertAssign` | Request | `POST /alerts/{id}/assign` body |
| `AccountOut` | Response | Account basic information |
| `AccountDNAOut` | Response | DNA vector + fraudster matches + reconstruction error |
| `TradeOut` | Response | Individual trade record |
| `AccountNetworkOut` | Response | Graph nodes and edges for network visualization |
| `CaseGenerateRequest` | Request | PDF case generation parameters |
| `CaseGenerateResponse` | Response | Case ID, number, PDF path, download URL |
| `SEBICaseOut` | Response | Full SEBI case record |
| `WeeklySummaryOut` | Response | Weekly surveillance statistics |

All schemas use `model_config = ConfigDict(from_attributes=True)` for SQLAlchemy ORM compatibility.

### `api/routers/alerts.py`
**Role:** All alert-related REST endpoints.

**Endpoints:**
- `GET /alerts` — Paginated, filterable alert list. Supports `status`, `min_score`, `scrip`, `from_date`, `to_date`, `limit`, `offset`
- `GET /alerts/live` — **Server-Sent Events (SSE)** live stream. Polls DB every 5 seconds for new alerts. Powers the real-time dashboard feed
- `GET /alerts/{alert_id}` — Single alert by UUID with full evidence detail
- `POST /alerts/{alert_id}/status` — Update alert workflow status
- `POST /alerts/{alert_id}/assign` — Assign alert to a named analyst

### `api/routers/accounts.py`
**Role:** Account-level surveillance endpoints.

**Endpoints:**
- `GET /accounts/search` — Search accounts by broker and/or flagged status with pagination
- `GET /accounts/{account_id}/dna` — Computes or retrieves the account's 32-dim behavioral DNA vector, runs similarity matching against known fraudsters, and returns `is_anomalous` flag
- `GET /accounts/{account_id}/trades` — Paginated trade history with optional date range filtering
- `GET /accounts/{account_id}/network` — Builds the temporal coincidence graph for an account and returns nodes/edges JSON for the network visualization (2-hop limit)

### `api/routers/reports.py`
**Role:** PDF report generation and case management endpoints.

**Endpoints:**
- `POST /reports/case/{alert_id}` — Generates a SEBI-compliant PDF case file for an alert. Creates a `SEBICase` DB record, calls the PDF generator, stores the path, returns download URL
- `GET /reports/case/{alert_id}/download` — Streams the PDF binary to the client for download
- `GET /reports/summary/weekly` — Returns 7-day surveillance statistics: total alerts, resolved, false positive rate, top manipulated scrips

---

## AI Models (`models/`)

### `models/gnn/tcn.py`
**Role:** Graph Neural Network architecture for Temporal Coincidence Network.

**Architecture:**
```
Trade DataFrame
    → build_trade_graph()             # Constructs PyG Data object
    → GraphData (nodes, edges, attrs) # Node: per-account features
    → TemporalCoincidenceNetwork      # 3-layer GAT model
       - GATConv(in=16, out=128, heads=4)
       - GATConv(in=512, out=64, heads=2)
       - GATConv(in=128, out=1, heads=1)
    → sigmoid activation
    → per-node manipulation scores [0, 1]
```

**`build_trade_graph(df, window_ms, min_coincidences)`:**
- Groups trades by time window
- Creates edges between accounts that traded same scrip within `window_ms` milliseconds
- Edge attributes: time delta, price similarity, volume ratio
- Returns `GraphData` namedtuple with edge_index, node features, account ID list

### `models/gnn/train_tcn.py`
**Role:** Training pipeline and model persistence for the TCN/GNN model.

**Key functions:**
- `train(data_path, epochs, lr)` — Full training loop with Adam optimizer, binary cross-entropy loss
- `evaluate(model, data)` — Computes precision, recall, F1 on test set
- `save_model(model, path)` — Saves state dict to `models/gnn/tcn_weights.pt`
- `load_model(path)` — **Called at API startup** to restore trained weights. Returns `None` gracefully if weights file doesn't exist
- `run_inference(model, trade_df)` — Applies trained model to new trade data, returns account-level scores
- `_generate_synthetic_graphs(n_normal, n_manipulated)` — Generates labeled PyG graph dataset for training

### `models/gnn/train_on_synthetic.py`
**Role:** Standalone script to train the GNN from scratch on synthetic fraud graphs.

Generates 50 manipulated + 50 normal graphs, trains for 30 epochs with:
- Adam optimizer (lr=1e-3, weight_decay=1e-4) + StepLR scheduler (step=10, γ=0.5)
- Gradient clipping at max norm 1.0
- NaN-guarded forward pass
- Best AUC-ROC checkpoint saving

```bash
python models/gnn/train_on_synthetic.py
```

### `models/dna/autoencoder.py`
**Role:** LSTM autoencoder for behavioral DNA fingerprinting.

**Architecture:**
```
Trade history (N trades) → feature_extractor → 32-dim feature vector
32-dim vector → Encoder LSTM (32→16→8) → latent 8-dim
latent 8-dim  → Decoder LSTM (8→16→32) → reconstruction
Reconstruction error = MSE(original, reconstructed)
```

**Key functions:**
- `extract_features(trade_df)` — Computes 32 behavioral metrics from trade history
- `get_autoencoder()` — Singleton loader; returns trained model or initializes fresh
- `BehavioralAutoencoder` class — PyTorch `nn.Module` with encode/decode/forward/reconstruction_error methods
- `encode(features)` — Returns the 32-dim DNA vector (the latent representation)
- `reconstruction_error(features)` — High error (> 0.5) = anomalous trader

**32 behavioral features include:** trade frequency, inter-trade intervals, volume distribution, price impact, scrip concentration, time-of-day patterns, order cancellation rate, average holding period.

### `models/dna/train_on_synthetic.py`
**Role:** Standalone script to train the DNA autoencoder from scratch on synthetic trade history data.

Generates normal and anomalous account trade sequences, trains the LSTM autoencoder, and saves weights to `models/dna/autoencoder_weights.pt`.

```bash
python models/dna/train_on_synthetic.py
```

### `models/dna/fingerprint_store.py`
**Role:** Database of known fraudster DNA vectors for similarity matching.

**`FingerprintStore` class:**
- `load_fraudster_dnas(db_session)` — Loads all `KnownFraudster` records from the database into memory as a numpy matrix
- `find_similar(dna_vector, threshold)` — Computes cosine similarity between a new account's DNA and all known fraudster vectors. Returns matches above `threshold` (default 0.85)
- `add_fraudster(name, dna_vector, scheme_type)` — Adds a new confirmed fraudster to the store

This store is loaded at API startup and held in `_app_state["fp_store"]` for fast in-memory similarity search.

### `models/cross_market/fusion.py`
**Role:** Cross-market phantom detector fusing signals from NSE, BSE, NFO, and MCX.

**Key functions:**
- `CrossMarketFusion` class — Main detector
- `fuse(nse_trades, bse_trades, nfo_trades, mcx_trades)` — Aligns timestamps across markets, computes correlation matrix
- `detect_phantom_trades(df)` — Identifies accounts with suspicious cross-market footprints
- `causal_inference(df)` — Uses DoWhy to test if cross-market activity is causally linked (not just correlated), reducing false positives
- `score(account_id, trade_data)` — Returns [0, 1] cross-market manipulation score

**Detection logic:**
- Lead-lag analysis: Does Account A's NSE trades systematically precede price moves in BSE?
- Volume anomaly: Sudden spike in one market coincident with opposite activity in derivative market
- Entity consolidation: Multiple accounts with same trading pattern across markets → likely same beneficial owner

### `models/zero_day/anomaly.py`
**Role:** Zero-day anomaly ensemble that detects novel, never-before-seen manipulation schemes.

**`ZeroDayDetector` class:**
- `fit(X)` — Trains all 4 sub-models on historical normal trading data
- `predict(X)` — Returns ensemble anomaly score (average of 4 model scores)
- `get_detector()` — Singleton accessor loaded at API startup

**Ensemble members:**
```python
models = {
    "iforest": IsolationForest(n_estimators=200, contamination=0.05),
    "lof":     LocalOutlierFactor(n_neighbors=20, novelty=True),
    "hbos":    HBOS(n_bins=10, contamination=0.05),
    "ocsvm":   OCSVM(kernel="rbf", nu=0.05)
}
```

**Feature space:** 20-dimensional vector per trade window including statistical moments, entropy of order flow, autocorrelation, price impact, and cross-account correlation.

---

## Data Layer (`data/`)

### `data/db/models.py`
**Role:** SQLAlchemy ORM model definitions — the database schema.

**Tables:**

| Table | Model | Purpose |
|---|---|---|
| `trades` | `Trade` | All individual trades ingested from NSE/BSE/broker feeds |
| `entities` | `Entity` | Legal entities (individuals, companies, HUFs) |
| `accounts` | `Account` | Trading accounts with DNA vectors and flagged status |
| `alerts` | `Alert` | Generated manipulation alerts with AI scores |
| `sebi_cases` | `SEBICase` | Formal SEBI case files linked to alerts |
| `known_fraudsters` | `KnownFraudster` | Database of confirmed fraudster DNA fingerprints |

**Enums defined:**
- `ExchangeEnum`: NSE, BSE, NFO, MCX
- `SideEnum`: BUY, SELL
- `EntityTypeEnum`: individual, company, huf
- `AlertStatusEnum`: open, investigating, closed, false_positive

**Dialect handling:** Handles both PostgreSQL (production) and SQLite (local dev). `ARRAY` columns use PostgreSQL's native ARRAY type in prod, and fall back to `JSON` columns in SQLite. `UUID` primary keys use PostgreSQL UUID type in prod and `String(36)` in SQLite.

### `data/db/session.py`
**Role:** SQLAlchemy engine and session factory.

**Smart fallback logic:**
1. Reads `POSTGRES_URL` from environment
2. Tests if PostgreSQL is actually reachable on `localhost:5432` (1-second timeout)
3. If unreachable → automatically switches to SQLite (`argus_dev.db` in project root)
4. Creates appropriate engine (SQLite uses `StaticPool` and `check_same_thread=False`)

**Exports:**
- `engine` — The SQLAlchemy engine (PostgreSQL or SQLite)
- `DATABASE_URL` — The active connection string
- `get_db()` — FastAPI dependency: yields a session, closes it after the request
- `get_session()` — Direct session factory for non-FastAPI code

### `data/db/crud.py`
**Role:** All database read/write operations. A complete data access layer keeping SQL out of the API routers.

**Functions:**
| Function | Purpose |
|---|---|
| `get_alert(db, alert_id)` | Fetch single alert by UUID |
| `get_alerts(db, **filters)` | Filtered, paginated alert listing |
| `update_alert_status(db, alert_id, status)` | Change alert workflow status |
| `assign_alert(db, alert_id, analyst)` | Assign to analyst |
| `count_alerts_today(db)` | Count of today's alerts |
| `get_account(db, account_id)` | Single account lookup |
| `search_accounts(db, **filters)` | Broker/flagged account search |
| `get_trades(db, **filters)` | Paginated trade history |
| `create_sebi_case(db, **kwargs)` | Create new SEBI case record |
| `get_sebi_case_by_alert(db, alert_id)` | Look up case by alert |
| `update_sebi_case_pdf(db, case_id, path)` | Store PDF path on case |
| `get_weekly_stats(db)` | Aggregate 7-day statistics |

### `data/ingest/nse_fetcher.py`
**Role:** Downloads and parses NSE market data.

**What it fetches:**
- **Bhavcopy** (daily equity price data) from NSE archives
- **F&O Bhavcopy** (futures and options data)
- **Bulk/Block Deals** (large institutional trades)
- **Participant-wise Open Interest** data

**Implementation:** Uses `requests` + `BeautifulSoup` to scrape NSE's archive pages. Parses CSV files into pandas DataFrames. Handles date formatting, retry logic, and deduplication.

### `data/ingest/bse_fetcher.py`
**Role:** Downloads and parses BSE market data.

**What it fetches:**
- BSE Bhavcopy (equity prices)
- Corporate announcements
- BSE bulk deals

Complements NSE data to enable cross-market detection. Data normalized to same schema as NSE output.

### `data/ingest/sebi_scraper.py`
**Role:** Scrapes SEBI enforcement orders and consent orders from `sebi.gov.in`.

**What it does:**
- Downloads SEBI enforcement orders (PDF)
- Extracts entity names, violation types, penalty amounts using `pdfplumber`
- Matches named entities against existing `Entity` records in the database
- Adds confirmed manipulators to the `KnownFraudster` table with their scheme type

This is how the system learns known bad actors and builds the fraudster DNA library.

### `data/ingest/mca_fetcher.py`
**Role:** Fetches corporate data from MCA21 (Ministry of Corporate Affairs).

**What it fetches:**
- Company master data (CIN, directors, registered address)
- Director identification numbers (DIN)
- Related company linkages

Used to build entity relationship graphs — identifying shell companies, common directors, and beneficial ownership chains used in circular trading schemes.

### `data/ingest/broker_feed.py`
**Role:** Real-time trade data feed from Zerodha/Kite broker API.

**What it does:**
- Authenticates using `ZERODHA_API_KEY` and `ZERODHA_ACCESS_TOKEN` from `.env`
- Subscribes to live tick data for a configured list of instruments
- Normalizes tick data to the standard trade schema
- Publishes to Kafka topic `trades.live`

### `data/pipeline/cleaner.py`
**Role:** Data cleaning and normalization for ingested records.

**Cleaning steps:**
- Deduplication by trade ID
- Timestamp normalization to UTC
- Price outlier detection and flagging
- Volume sanity checks (negative volume, zero price)
- Schema validation against expected column types
- Scrip symbol standardization (NSE symbol ↔ BSE symbol mapping)

### `data/pipeline/kafka_producer.py`
**Role:** Publishes trade records to Kafka topics.

**Topics produced:**
- `trades.live` — Real-time broker feed trades
- `trades.historical` — Batch-loaded historical trades

Uses `msgpack` serialization for efficient binary encoding. Includes retry logic and delivery confirmation.

### `data/pipeline/kafka_consumer.py`
**Role:** The Kafka consumer worker process. Runs as `argus-worker` container.

**What it does:**
- Subscribes to `trades.live` and `trades.historical` Kafka topics
- Deserializes incoming trade records
- Runs them through the cleaning pipeline
- Writes to the PostgreSQL `trades` table
- Triggers the scoring engine for real-time alerting
- Handles consumer group rebalancing and offset commits

---

## Scoring Engine (`scoring/`)

### `scoring/alert_engine.py`
**Role:** Orchestrates all 4 AI engines and generates alerts. The central coordinator of ARGUS.

**`AlertEngine` class:**
- `run(trade_window_df)` — Main entry point. Takes a window of recent trades (last 5 minutes), runs all 4 models, computes weighted score, creates alert if threshold exceeded
- `_run_gnn(df)` → GNN manipulation scores per account
- `_run_dna(df)` → DNA anomaly scores
- `_run_cross_market(df)` → Cross-market fusion scores
- `_run_zero_day(df)` → Zero-day ensemble scores
- `_fuse_scores(gnn, dna, cm, zd)` → Weighted combination
- `_create_alert(db, score, accounts, scrip)` → Writes `Alert` record to database
- `_determine_scheme_type(scores)` → Classifies the scheme (pump & dump, spoofing, etc.) based on score patterns

**Alert creation conditions:**
- Overall score ≥ `ALERT_SCORE_THRESHOLD` (default 7.5)
- At least 2 accounts involved
- Activity in the last `DETECTION_WINDOW_MINUTES` (default 5)

### `scoring/impossibility.py`
**Role:** Statistical impossibility detectors that boost alert scores for physically or probabilistically impossible patterns.

**Detectors:**
| Detector | Trigger | Score Boost |
|---|---|---|
| `exact_timestamp` | Multiple unrelated accounts trade at exactly the same millisecond | ×1.8 |
| `perfect_price_improvement` | Sequence of trades at perfectly incrementing prices | ×1.6 |
| `liquidity_exhaustion` | Single order absorbs exactly 100% of visible liquidity | ×1.5 |
| `synchronized_cancellation` | Multiple accounts cancel orders within same millisecond | ×1.7 |
| `zero_market_impact` | Large trade with statistically zero price impact | ×1.4 |

Also exposes `compute_poisson_impossibility()` and `compute_composite_score()` for direct use in verification and testing.

---

## Streamlit Dashboard (`dashboard/`)

A **Streamlit** multi-page surveillance dashboard providing a quick-launch, no-build alternative to the React dashboard. Suitable for internal analyst use and rapid prototyping.

### `dashboard/app.py`
**Role:** Main entry point. Configures the dark military-grade UI, handles API authentication (auto-fetches JWT token on startup), shows live system health status in the sidebar, and routes to the selected page.

```bash
# Run Streamlit dashboard
streamlit run dashboard/app.py
# Opens at http://localhost:8501
```

**Sidebar features:**
- ARGUS logo + tagline
- Live system status indicator (🟢/🔴)
- Last scan timestamp
- Model load status per engine
- Navigation radio (4 pages)

### `dashboard/pages/live_alerts.py`
**Role:** Real-time alert feed page. Polls the API for current alerts, renders filterable metric cards (by scheme type and status), expandable alert rows showing all 4 AI engine scores, and a **FREEZE AND INVESTIGATE** action button.

### `dashboard/pages/account_dna.py`
**Role:** Behavioral analysis page. Accepts an account ID input, fetches the DNA vector from the API, and renders: a Plotly radar chart of behavioral features, reconstruction error gauge, fraudster similarity match results, and a paginated trade history table.

### `dashboard/pages/network_graph.py`
**Role:** Interactive trading network visualization. Fetches the temporal coincidence graph for a given account and renders an interactive network using **PyVis** (embedded as HTML). Flagged accounts shown in red, normal accounts in blue, edge thickness proportional to coincidence frequency.

### `dashboard/pages/case_builder.py`
**Role:** SEBI case preparation interface. Lets analysts select an alert, fill in entity names, date range, estimated unlawful gains, and investigator notes, then triggers PDF generation via the API and provides a download link for the generated report.

---

## React Dashboard (`argus-dashboard/`)

Built with **React 18, Vite, Tailwind CSS, D3.js, Recharts, and Framer Motion** — a high-performance, dark military-grade terminal web dashboard for surveillance officers.

**Tech stack:** React 18.3, React Router 6, React Query, Zustand, Axios, D3 v7, Recharts, Framer Motion, date-fns, react-hot-toast.

### `src/App.jsx`
**Role:** React entrypoint. Sets up React Router, React Query client (30s auto-refetch), and the main layout shell with `Sidebar` and `TopBar`. Routes:

| Path | Page |
|---|---|
| `/alerts` | LiveAlerts (default) |
| `/dna` | AccountDNA |
| `/network` | NetworkView |
| `/cases` | CaseBuilder |
| `/summary` | WeeklySummary |

### Pages (`src/pages/`)

#### `LiveAlerts.jsx`
Real-time alert dashboard. Uses `EventSource` to subscribe to the live SSE stream (`/alerts/live`). Displays metric cards, sortable/filterable alert table with `SchemeBadge` and `ScoreBar`, and expandable rows showing all 4 engine score breakdowns.

#### `AccountDNA.jsx`
Behavioral analysis page. Fetches DNA vectors and renders a `RadarChart` (8-axis behavioral profile), `ScoreGauge` for reconstruction error, fraudster similarity bars, and an interactive trade history table with sortable columns.

#### `NetworkView.jsx`
Interactive network graph using **D3.js** force-directed simulation. Visualizes the temporal coincidence graph: flagged accounts pulse red, edges weighted by coincidence count. Supports zoom/pan and node click to drill into account detail.

#### `CaseBuilder.jsx`
SEBI case preparation interface. Uses `CaseModal` component. Analysts select alerts, fill out entity/gain/notes fields, and trigger PDF generation. Shows case status badge and download link on success.

#### `WeeklySummary.jsx`
7-day surveillance statistics page. Fetches `/reports/summary/weekly` and renders: total alert volume trend (area chart), scheme type breakdown (bar chart), false positive rate gauge, top manipulated scrips table, and analyst workload distribution.

### Components (`src/components/`)

| Component | Purpose |
|---|---|
| `Sidebar.jsx` | Collapsible dark sidebar with navigation links, system status indicator, and model version badges |
| `TopBar.jsx` | Header bar with alert count badge, search input, and live clock |
| `AlertRow.jsx` | Expandable alert table row with score bars and action buttons |
| `CaseModal.jsx` | Full-screen modal for SEBI case creation with form validation |
| `MetricCard.jsx` | Stat card with animated number transitions |
| `NetworkGraph.jsx` | D3.js force-layout graph component with zoom and highlight |
| `RadarChart.jsx` | Recharts radar chart for 8-axis DNA behavioral profile |
| `ScoreBar.jsx` | Horizontal progress bar for individual engine scores |
| `ScoreGauge.jsx` | Circular gauge for overall manipulation score (0–10) |
| `SchemeBadge.jsx` | Color-coded badge for scheme type classification |
| `LivePulse.jsx` | Animated pulsing dot indicator for live stream status |

### `src/api/client.js`
**Role:** Axios integration with auto-authentication interceptors and a full **Mock Data Layer** (`VITE_USE_MOCK=true`) for pitch-ready offline demonstrations.

---

## Reports (`reports/`)

### `reports/pdf_generator.py`
**Role:** Generates SEBI-compliant PDF case reports using `reportlab`.

**`generate_case_pdf(alert, case, output_path)` produces a multi-page PDF containing:**

1. **Cover Page** — ARGUS logo, case number, date, entity names, scrip
2. **Executive Summary** — Overall score, scheme classification, detected pattern description
3. **Score Breakdown** — Bar chart of all 4 AI engine scores
4. **Account Network Diagram** — Static render of the trading ring
5. **Trade Evidence Table** — Timestamped suspicious trades with account IDs
6. **Score Methodology** — Explanation of the weighted formula
7. **Statutory Reference** — Relevant SEBI regulations violated (PFUTP, SAST, Insider Trading Regs)
8. **Appendix** — Raw data tables, model confidence intervals

PDFs are stored in `REPORTS_DIR` (default `/tmp/argus_reports/`, configurable via env var) and the path is stored in the `SEBICase` database record.

---

## Database Migrations (`alembic/`)

### `alembic/env.py`
**Role:** Alembic environment configuration. Imports ARGUS models (`data/db/models.py`) so Alembic can auto-generate migration scripts by comparing the ORM models against the live database schema.

### `alembic/versions/001_initial.py`
**Role:** First migration — creates all tables from scratch. Defines the initial schema with all columns, types, indexes, and foreign keys for `trades`, `entities`, `accounts`, `alerts`, `sebi_cases`, and `known_fraudsters`.

**To run migrations:**
```bash
# Apply all pending migrations
.venv\Scripts\python.exe -m alembic upgrade head

# Create a new migration after changing models.py
.venv\Scripts\python.exe -m alembic revision --autogenerate -m "description"

# Rollback one migration
.venv\Scripts\python.exe -m alembic downgrade -1
```

---

## Tests (`tests/`)

### `tests/test_api.py`
**Role:** Integration tests for the FastAPI API.

**Tests cover:**
- `POST /auth/token` — Valid login, invalid credentials, missing fields
- `GET /health` — Returns valid structure
- `GET /alerts` — Authenticated + unauthenticated access
- `POST /alerts/{id}/status` — Status transitions
- `GET /accounts/search` — Filter combinations
- `POST /reports/case/{id}` — PDF generation trigger

Uses `httpx.AsyncClient` with `TestClient`. Database is mocked using SQLite in-memory.

### `tests/test_gnn.py`
**Role:** Unit tests for the GNN/TCN model.

**Tests cover:**
- `build_trade_graph()` — Correct number of nodes, edge formation within time window
- `TemporalCoincidenceNetwork.forward()` — Output shape, value range [0,1]
- `run_inference()` — Returns per-account scores
- Edge case: single account, no edges, all same-scrip trades

### `tests/test_dna.py`
**Role:** Unit tests for the DNA autoencoder and fingerprint store.

**Tests cover:**
- `extract_features()` — 32-dim output, handles missing data
- `BehavioralAutoencoder.encode()` — Latent vector dimensionality
- `BehavioralAutoencoder.reconstruction_error()` — Higher for anomalous sequences
- `FingerprintStore.find_similar()` — Cosine similarity thresholding
- Deterministic encoding: same input → same DNA vector

### `tests/test_scoring.py`
**Role:** Unit tests for the scoring and alerting engine.

**Tests cover:**
- Score weighting formula correctness
- Threshold triggering (≥ 7.5 creates alert, < 7.5 does not)
- `impossibility.py` boost factors applied correctly
- `AlertEngine.run()` end-to-end with mocked models
- Scheme type classification from score patterns

**To run tests:**
```bash
.venv\Scripts\python.exe -m pytest tests/ -v
```

---

## Demo (`demo/`)

### `demo/run_demo.py`
**Role:** Command-line demo runner. Executes pre-built fraud scenarios against the live API.

```bash
# Run all demo cases
python demo/run_demo.py --case all

# Run specific scheme
python demo/run_demo.py --case pump_and_dump
python demo/run_demo.py --case circular_trading
python demo/run_demo.py --case spoofing
```

### `demo/synthetic_fraud.py`
**Role:** Generates synthetic but realistic fraud data for demo and training purposes.

Two generators:
- `generate_random_trades(n_accounts, n_trades, scrip)` — Non-manipulated Poisson-timed trades for normal baseline
- `generate_coordinated_trades(n_colluding, n_bursts, window_ms, scrip)` — Coordinated burst trades with colluding accounts within a configurable millisecond window, mixed with innocent background trades

Output is normalized trade DataFrames compatible with the scoring engine and GNN training pipeline.

### `demo/real_cases/`
**Role:** Self-contained detection scenarios modeled on real manipulation patterns from SEBI enforcement orders (entity names redacted). Each file generates synthetic data matching the documented scheme and runs the full detection pipeline.

| File | Scenario | Detection Focus |
|---|---|---|
| `case_pump_dump.py` | XYZLTD pump & dump over 3 days | GNN burst coordination + Zero-Day price spike |
| `case_circular_trading.py` | 5-entity circular trading ring | GNN ring topology + DNA wash-trading fingerprint |
| `case_spoofing.py` | Large-order spoofing on illiquid scrip | GNN order imbalance + impossibility boosters |

Each exposes `run_detection()` → returns `{"overall_score": float, "scheme_type": str, "accounts_involved": list}`.

---

## Database Schema

```
trades
├── id (UUID PK)
├── account_id (String, FK→accounts)
├── scrip (String, indexed)
├── exchange (Enum: NSE/BSE/NFO/MCX)
├── timestamp (DateTime TZ, indexed)
├── price (Float)
├── volume (Float)
├── side (Enum: BUY/SELL)
├── order_type (String, nullable)
├── is_manipulated (Boolean, default=False)
└── created_at (DateTime)

accounts
├── id (String PK)
├── broker (String)
├── pan_hash (String, unique)
├── entity_id (UUID FK→entities)
├── behavioral_dna (Array[Float] / JSON)
├── dna_updated_at (DateTime)
├── is_flagged (Boolean)
└── flag_reason (String)

alerts
├── id (UUID PK)
├── scrip (String)
├── exchange (String)
├── detected_at (DateTime)
├── impossibility_score (Float)
├── scheme_type (String)
├── accounts_involved (Array[String] / JSON)
├── gnn_score (Float)
├── dna_score (Float)
├── cross_market_score (Float)
├── zero_day_score (Float)
├── status (Enum: open/investigating/closed/false_positive)
├── case_file_path (String)
├── assigned_to (String)
└── created_at (DateTime)

sebi_cases
├── id (UUID PK)
├── alert_id (UUID FK→alerts)
├── case_number (String, unique)   # Format: ARGUS/YYYY/XXXXXXXX
├── entity_names (Array[String] / JSON)
├── scrip (String)
├── from_date (Date)
├── to_date (Date)
├── estimated_gain (Float)
├── evidence_json (JSON)
├── status (String: draft/filed/closed)
├── pdf_path (String)
└── created_at (DateTime)

known_fraudsters
├── id (UUID PK)
├── entity_name (String)
├── sebi_order_ref (String)
├── scheme_type (String)
├── behavioral_dna (Array[Float] / JSON)
├── scrips_involved (Array[String] / JSON)
├── conviction_date (Date)
└── source_url (String)
```

---

## Data Sources

| Source | Fetch Method | Frequency | Data Type |
|---|---|---|---|
| NSE Bhavcopy | HTTP download | Daily (EOD) | Equity prices, volumes |
| NSE F&O Bhavcopy | HTTP download | Daily (EOD) | Futures & options data |
| NSE Bulk Deals | HTTP scrape | Daily | Large institutional trades |
| BSE Bhavcopy | HTTP download | Daily (EOD) | BSE equity prices |
| BSE Announcements | HTTP scrape | Intraday | Corporate events |
| SEBI Orders | PDF scrape | Weekly | Enforcement actions |
| MCA21 | HTTP API | On-demand | Company/director data |
| Zerodha/Kite | WebSocket | Real-time | Live trade ticks |
| Kafka topics | Consumer | Real-time | Aggregated tick stream |

---

## API Reference

### Authentication

```http
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=admin&password=argus2024
```

Response: `{ "access_token": "eyJ...", "token_type": "bearer" }`

All subsequent requests: `Authorization: Bearer <token>`

### Full Endpoint Table

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/token` | ❌ | Get JWT token |
| GET | `/health` | ❌ | System health & model status |
| GET | `/alerts` | ✅ | List alerts (paginated, filtered) |
| GET | `/alerts/live` | ✅ | SSE real-time alert stream |
| GET | `/alerts/{id}` | ✅ | Single alert detail |
| POST | `/alerts/{id}/status` | ✅ | Update status |
| POST | `/alerts/{id}/assign` | ✅ | Assign to analyst |
| GET | `/accounts/search` | ✅ | Search accounts |
| GET | `/accounts/{id}/dna` | ✅ | Behavioral DNA + fraudster match |
| GET | `/accounts/{id}/trades` | ✅ | Trade history |
| GET | `/accounts/{id}/network` | ✅ | 2-hop network graph |
| POST | `/reports/case/{id}` | ✅ | Generate SEBI PDF case |
| GET | `/reports/case/{id}/download` | ✅ | Download PDF |
| GET | `/reports/summary/weekly` | ✅ | 7-day statistics |

---

## Quick Start — Local Dev

**Prerequisites:** Python 3.11, Git

```bash
# 1. Enter project directory
cd d:\argus

# 2. Activate virtual environment
.venv\Scripts\Activate.ps1

# 3. Install dependencies (if not already done)
pip install -r requirements.txt

# 4. Verify the full system (optional but recommended)
python verify_argus.py

# 5. Start the API server
python -m uvicorn api.main:app --host 127.0.0.1 --port 8080 --reload

# 6. Open Swagger UI
# http://127.0.0.1:8080/docs

# 7. Login credentials
# Username: admin
# Password: argus2024 (or ADMIN_PASSWORD from .env)
```

**Local dev uses SQLite automatically** — no PostgreSQL, Redis, or Kafka needed to start the API.

> **Option A — Streamlit Dashboard** (simplest, no build step):
> ```bash
> streamlit run dashboard/app.py
> # Opens at http://localhost:8501
> ```

> **Option B — React Dashboard** (full-featured terminal UI):
> ```bash
> cd argus-dashboard
> npm run dev
> # Opens at http://localhost:5173
> ```

> **Run detection demo:**
> ```bash
> python demo/run_demo.py --case all
> ```

> **Retrain models on synthetic data:**
> ```bash
> python models/gnn/train_on_synthetic.py
> python models/dna/train_on_synthetic.py
> ```

---

## Docker Deployment

**Prerequisites:** Docker Desktop, Docker Compose

```bash
# 1. Copy environment template
cp .env.example .env
# Edit .env with production values

# 2. Build and start all services
docker-compose up --build -d

# 3. Check all services are healthy
docker-compose ps

# 4. Access points
# Dashboard:  http://localhost:5173
# API docs:   http://localhost:8080/docs

# 5. Run database migrations
docker-compose exec argus-api alembic upgrade head

# 6. Run demo detection
docker-compose exec argus-api python demo/run_demo.py --case all

# 7. View API logs
docker-compose logs -f argus-api

# 8. Stop everything
docker-compose down
```

---

## Current Status

**As of April 2026 — Fully Operational 🚀**

| Component | Status | Notes |
|---|---|---|
| **GNN / TCN Model** | ✅ Trained | `tcn_weights.pt` (345 KB) — trained on synthetic fraud graphs |
| **DNA Autoencoder** | ✅ Trained | `autoencoder_weights.pt` (341 KB) — trained on synthetic trade sequences |
| **Zero-Day Ensemble** | ✅ Operational | Fit-on-demand; no weights file required |
| **Cross-Market Fusion** | ✅ Operational | DoWhy causal inference enabled |
| **Scoring Engine** | ✅ Upgraded | Poisson null model + impossibility boosters |
| **FastAPI API** | ✅ Running | Port 8080, JWT auth, SSE live stream |
| **Streamlit Dashboard** | ✅ Running | Port 8501, 4 pages, dark military theme |
| **React Dashboard** | ✅ Running | Port 5173, 5 pages, 11 components, D3.js graphs |
| **SEBI PDF Generator** | ✅ Working | 8-page case reports with evidence tables |
| **SQLite DB** | ✅ Active | Auto-created on startup; `argus_dev.db` present |
| **Demo Scenarios** | ✅ Live | 3 real-case scenarios verified end-to-end |
| **Verification Suite** | ✅ 10/10 | `verify_argus.py` passes all checks |

**Functional highlights:**
- ✅ **Dual Dashboard**: Both Streamlit (quick-launch) and React (pitch-grade terminal UI) fully operational.
- ✅ **Trained Models**: GNN and DNA autoencoder have saved weights; load at API startup in < 1 second.
- ✅ **High-Performance Graph Build**: O(n²) loops eliminated; graph construction < 1s on 1000-trade windows.
- ✅ **Real-Case Detection**: `pump_and_dump`, `circular_trading`, and `spoofing` scenarios produce correct scheme type classification with non-NaN scores.
- ✅ **Offline Demo Mode**: React dashboard runs on mock data (`VITE_USE_MOCK=true`) for pitch presentations without a live API.
- ✅ **PDF Reports**: SEBI-compliant 8-page case PDFs generate successfully (verified via `verify_argus.py` step 7).

---

## Known Limitations

1. **No PostgreSQL locally** — Running on SQLite. `ARRAY` columns stored as JSON; UUID keys stored as strings. Functionally equivalent for dev; deploy with PostgreSQL for production
2. **Redis not installed** — Health check shows `redis: error`. This only affects response caching; all endpoints work without it
3. **No Kafka locally** — Real-time broker feed ingestion not active. Historical data must be loaded via scripts
4. **Model weights are synthetic-only** — `tcn_weights.pt` and `autoencoder_weights.pt` were trained on procedurally generated data, not labeled real SEBI enforcement data. Precision/recall on real market data is unknown until labeled historical data is ingested and models are retrained
5. **Single admin user** — Auth is admin-only in dev. Production should add a proper users table with roles
6. **PyTorch-Geometric** — `pyg-lib` (C++ speedup extension) removed from requirements as no Windows pre-built wheel exists. GNN still works via the pure-Python fallback, just slightly slower
7. **SEBI PDF reports** — Require at least one alert record in the database. Empty DB means no alerts to report on until data is ingested
8. **Streamlit dashboard API URL** — Defaults to `http://argus-api:8000` (Docker service name). Override via `ARGUS_API_URL` env var when running locally: `ARGUS_API_URL=http://127.0.0.1:8080 streamlit run dashboard/app.py`

---

## Roadmap

### Phase 1 — Production Infrastructure
- [ ] Install and configure PostgreSQL locally
- [ ] Set up Redis for real-time SSE caching and alert pub/sub
- [ ] Deploy Kafka for live trade stream ingestion
- [ ] Run `alembic upgrade head` to apply migrations to PostgreSQL
- [ ] Configure Nginx reverse proxy for HTTPS

### Phase 2 — Data Ingestion
- [ ] Schedule NSE/BSE Bhavcopy daily downloads (cron/Task Scheduler)
- [ ] Configure Zerodha Kite API keys for live feed
- [ ] Import SEBI enforcement database into `known_fraudsters` table
- [ ] Ingest MCA21 entity linkage data for beneficial ownership mapping

### Phase 3 — Model Training on Real Data
- [ ] Label historical trade data using SEBI orders as ground truth
- [ ] Retrain GNN on labeled real fraud graphs (replace synthetic weights)
- [ ] Retrain DNA autoencoder on 6+ months of real clean trade data
- [ ] Calibrate zero-day ensemble contamination rate against real base rate
- [ ] Validate precision/recall on held-out confirmed SEBI cases

### Phase 4 — Dashboard & Reporting ✅ (Complete)
- [x] Build Streamlit multi-page surveillance dashboard
- [x] Build React/Vite high-performance terminal dashboard (5 pages, 11 components)
- [x] Implement D3.js network graph with force simulation
- [x] Implement DNA radar chart and score gauges
- [x] PDF generation end-to-end verified
- [ ] Connect React live alerts to Redis pub/sub (currently polling)
- [ ] Add SEBI email notification on critical alerts (score ≥ 9.0)

### Phase 5 — Docker & Production Deploy
- [ ] Install Docker Desktop
- [ ] Build and validate all Docker images
- [ ] Set production secrets in `.env`
- [ ] Deploy with `docker-compose up --build -d`
- [ ] Run `verify_argus.py` inside container to confirm operational status

---

## Contributing

This project follows a modular architecture. Each AI engine is fully independent:

- Add a new detection model → create `models/<name>/` with `__init__.py` + model file + `train_on_synthetic.py`
- Update scoring weights → edit `scoring/alert_engine.py` weights dict
- Add a new API endpoint → create or extend a router in `api/routers/`
- Add a data source → create a new fetcher in `data/ingest/`
- Add a Streamlit page → create `dashboard/pages/<name>.py` and expose a `render(api_base, token)` function
- Add a React page → create `argus-dashboard/src/pages/<Name>.jsx` and register in `App.jsx`

---

## License

Proprietary — ARGUS is an enterprise system. All rights reserved.

---

*Built with PyTorch, FastAPI, SQLAlchemy, React 18, Tailwind CSS, D3.js, Recharts, Framer Motion, torch-geometric, pyod, dowhy, reportlab, streamlit, pyvis, and the full scientific Python stack.*
