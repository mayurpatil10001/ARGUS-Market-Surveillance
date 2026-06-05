# ARGUS Market Surveillance

> **Enterprise-Grade AI System for Real-Time Indian Market Surveillance & PS-402 Digital Threat Detection**  
> Built for SEBI, NSE, BSE regulatory teams, compliance departments, and the NEOFuture Hackathon (PS-402).

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3.0-orange)](https://pytorch.org)
[![torch-geometric](https://img.shields.io/badge/torch--geometric-2.5.3-red)](https://pyg.org)
[![boto3](https://img.shields.io/badge/boto3-%3E%3D1.34-yellow)](https://boto3.amazonaws.com)
[![License](https://img.shields.io/badge/License-Proprietary-red)](#)
[![Status](https://img.shields.io/badge/Status-29%2F29%20Verified-brightgreen)](#current-status)
[![Version](https://img.shields.io/badge/Version-v2.4.1-blue)](#current-status)

---

## Table of Contents

1. [What is ARGUS / SENTINEL?](#what-is-argus--sentinel)
2. [System Architecture](#system-architecture)
3. [AI Engines](#ai-engines)
4. [Detection Capabilities](#detection-capabilities)
5. [Scoring Formula](#scoring-formula)
6. [Project Structure](#project-structure--every-file-explained)
   - [Root Files](#root-level-files)
   - [API Layer (`api/`)](#api-layer-api)
   - [AI Models (`models/`)](#ai-models-models)
   - [Data Layer (`data/`)](#data-layer-data)
   - [Scoring Engine (`scoring/`)](#scoring-engine-scoring)
   - [Streamlit Dashboard (`dashboard/`)](#streamlit-dashboard-dashboard)
   - [Legacy React Dashboard (`argus-dashboard/`)](#legacy-react-dashboard-argus-dashboard)
   - [Next.js Dashboard (`argus-main/`)](#nextjs-dashboard-argus-main)
   - [Reports (`reports/`)](#reports-reports)
   - [Database Migrations (`alembic/`)](#database-migrations-alembic)
   - [Tests (`tests/`)](#tests-tests)
   - [Demo (`demo/`)](#demo-demo)
   - [Infrastructure (`infra/`)](#infrastructure-infra)
7. [Database Schema](#database-schema)
8. [PS-402 Ingestion API](#ps-402-ingestion-api)
9. [Document Threat Analyzer](#document-threat-analyzer)
10. [Data Sources](#data-sources)
11. [API Reference](#api-reference)
12. [Quick Start — Local Dev](#quick-start--local-dev)
13. [Docker Deployment](#docker-deployment)
14. [AWS Deployment](#aws-deployment)
15. [Current Status](#current-status)
16. [Known Limitations](#known-limitations)
17. [Roadmap](#roadmap)

---

## What is ARGUS / SENTINEL?

**ARGUS** (**A**daptive **R**egulatory **G**raph for **U**nseen **S**urveillance) is an enterprise AI system that monitors Indian capital markets in real-time and automatically detects market manipulation schemes before or as they happen. It has been extended into **SENTINEL** for the NEOFuture Hackathon PS-402 challenge — adding a full digital threat detection layer (phishing, social manipulation, misinformation) plus an MRFE document analyzer and 5-scenario simulation engine.

It combines **7 independent AI engines** — graph neural networks, behavioral biometrics, cross-market fusion, zero-day anomaly detection, social media signal analysis, financial misinformation detection, and the Market Reaction Fingerprint Engine (MRFE) — into a composite score that triggers alerts for SEBI enforcement action.

**Core purpose:**
- Detect pump & dump, spoofing, layering, circular trading, and insider trading signals
- Ingest and score threats from social media, news, phishing URLs, and generic platform activity
- Detect coordinated financial misinformation and market-moving fake news
- Analyze uploaded documents (PDF/DOCX/TXT) for financial threats via the Document Threat Analyzer (PS-402 pipeline)
- Analyze text, PDF, TXT, CSV, and DOCX documents for financial threats (MRFE engine)
- Run full-pipeline stress tests with 5 synthetic threat scenarios (Simulation Engine)
- Generate SEBI-compliant case reports with evidence automatically; upload to S3 with presigned URLs
- Provide real-time surveillance dashboards (Next.js 16 + Streamlit + Legacy React) for market regulators
- Build behavioral DNA fingerprints of traders to identify repeat offenders
- Deploy to AWS with full infrastructure-as-code (Terraform) and zero-downtime CI/CD

---

## System Architecture

```
                ┌───────────────────┬────────────────────────┐
                │                   │                        │
       ┌────────▼────────┐  ┌───────▼──────────┐  ┌─────────▼──────────┐
       │   FastAPI API   │  │  Next.js 16 UI   │  │  React/Vite UI     │
       │   api/main.py   │  │  argus-main/     │  │  argus-dashboard/  │
       │   Port 8000     │  │  Port 3000       │  │  Port 5173         │
       └────────┬────────┘  └──────────────────┘  └────────────────────┘
                │     ┌───────────────────┐
       ┌────────▼────┐│  Streamlit UI     │
       │  PDF Reports││  dashboard/app.py │
       │reports/pdf_ ││  Port 8501        │
       │generator.py ││                  │
       └─────────────┘└──────────────────┘
```

**5 Routers:** `/alerts` (+ simulate), `/accounts`, `/reports`, `/ps402` (+ analyze-document), `/mrfe`  
**2 DB tables:** `alerts` (30+ cols), `market_signals` (14 cols)  
**7 AI engines** loaded at startup via FastAPI lifespan context manager  
**2 React frontends:** Next.js 16 (`argus-main/`) — primary pitch dashboard; Vite/React (`argus-dashboard/`) — terminal-style legacy UI

---

## AI Engines

ARGUS now runs **7 AI engines** — 4 core financial manipulation detectors, 2 digital threat engines added in PS-402, plus the new MRFE document analyzer.

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

### 5. Social Signal Fetcher
**Supplementary score: `social_signal_score` on Alert**

Monitors social media platforms (Twitter/X, Reddit, WhatsApp-forwarded content) for coordinated financial manipulation signals — pump groups, coordinated buy alerts, and operator-driven FOMO campaigns.

**How it works:**
- Keyword scoring for high-risk financial language (pump, circuit, guaranteed, operator, multibagger, etc.)
- Engagement velocity analysis: sudden spike in posts about a scrip → manipulation signal
- Cross-platform deduplication and source credibility weighting
- Returns `social_signal_score` ∈ [0, 1] stored on the `Alert` record

**Module:** `data/ingest/social_signal_fetcher.py`

### 6. Financial Misinformation Detector
**Supplementary score: `misinfo_score` on Alert**

A **TF-IDF + Logistic Regression** classifier trained on labeled synthetic financial text data. Detects fake financial news, unverified insider claims, SEBI impersonation, and pump-and-dump promotional content in news headlines, social posts, and brokerage messages.

**How it works:**
- Synthetic training corpus: 35 legitimate news samples + 35 misinformation samples, augmented 4-6× with word-swap noise
- TF-IDF vectorizer (1–3 ngrams, 8,000 features, sublinear TF scaling)
- Logistic Regression (C=1.0, class_weight=balanced, lbfgs solver)
- Cross-validated F1 > 0.90 on synthetic held-out data
- Weights persisted to `models/misinfo/misinfo_weights.pkl`; trained inline on first run if missing
- Returns `misinfo_score` ∈ [0, 1] stored on the `Alert` record

**Modules:** `models/misinfo/detector.py`, `models/misinfo/train_on_synthetic.py`

### Generic Digital Threat Adapter
**Universal normalizer for non-financial threat signals**

Accepts phishing URLs, suspicious transaction logs, and generic platform activity logs and normalizes them into the standard ARGUS threat schema (entity_id, timestamp, threat_type, platform, raw_signal, threat_score). Auto-detects threat type from signal structure.

**Supported threat types:** `market_manipulation`, `social_media_threat`, `misinformation`, `phishing`, `generic_digital_threat`

**Module:** `data/ingest/generic_threat_adapter.py`

### 7. Market Reaction Fingerprint Engine (MRFE)
**New in v2.1 — Document threat analyzer**

Accepts **text, PDF, TXT, CSV, and DOCX inputs** and returns a structured financial threat analysis. MRFE integrates all three existing AI sub-systems (misinfo detector, social signal scorer, threat adapter) into a single composited heuristic threat score, classifies the financial event type, extracts affected NSE/BSE scrips via regex, and recommends an enforcement action.

**Output fields:** `event_type`, `threat_score`, `misinfo_score`, `social_score`, `threat_adapter_score`, `market_impact` (low/medium/high/critical), `affected_scrips`, `recommended_action`, `confidence`, `evidence_snippets`, `processing_time_ms`.

> All scores are **heuristic estimates** from ARGUS detection modules — not validated accuracy percentages.

**Modules:** `models/mrfe/__init__.py`, `models/mrfe/engine.py`, `api/routers/mrfe.py`

### Simulation Engine
**New in v2.1 — Full system demo harness**

Runs **5 synthetic threat scenarios** (pump_dump, spoofing, circular_trading, social_manipulation, phishing_campaign) through the complete ARGUS detection pipeline. Creates real DB records (alerts and market_signals) and measures detection latency per scenario. All generated data is clearly labeled `synthetic_data_used: true`.

**Module:** `scoring/simulation_engine.py`, endpoint: `POST /alerts/simulate`

---

## Detection Capabilities

| Scheme | Primary Engine | Description |
|---|---|---|
| **Pump & Dump** | GNN + Zero-Day | Coordinated buying to inflate price, then mass sell |
| **Spoofing** | GNN | Placing large orders to move price, then cancelling |
| **Layering** | GNN | Multiple spoof orders at different price levels |
| **Circular Trading** | GNN + DNA | Ring of trades between related accounts; no economic purpose |
| **Insider Trading** | DNA + Cross-Market | Abnormal pre-announcement activity across markets |
| **Social Manipulation** | Social Signal | Coordinated pump campaigns on Reddit/Twitter/WhatsApp |
| **Financial Misinformation** | Misinfo Detector | Fake news, SEBI impersonation, promotional content |
| **Phishing** | Generic Threat Adapter + PS-402 | Spoofed broker/SEBI domains |
| **Coordinated Bot Attack** | GNN + Social Signal | Inauthentic mass account activity |
| **Document Threats** | MRFE | PDF/text/CSV threat classification |

---

## Scoring Formula

The composite **impossibility score** (0–10) is calculated as:

```
  0.35 × TCN/GNN Score
+ 0.25 × Zero-Day Ensemble Score
+ 0.25 × DNA Autoencoder Score
+ 0.15 × Cross-Market Fusion Score
```

**Supplementary scores** (stored on Alert, not included in main composite):
```
social_signal_score  [0–1]  — coordinated social media campaign strength
misinfo_score        [0–1]  — financial misinformation probability
```
These supplement the investigation record and can independently elevate alert priority.

**Alert Threshold:** Overall Score ≥ **7.5** → Alert created & sent to dashboard

The `impossibility.py` module applies multiplicative boosters for statistically impossible patterns:
- Exact-same timestamp trades across unrelated accounts → ×1.8
- Order size precisely matching available liquidity → ×1.5
- Perfect price improvement sequence → ×1.6

---

## Project Structure — Every File Explained

```
argus/
├── api/                      # FastAPI backend
│   ├── main.py               # App entry, /health, /auth/token, lifespan (7 engines)
│   ├── auth.py               # JWT auth dependency (circular-import-safe)
│   ├── schemas.py            # All Pydantic v2 schemas incl. MRFE + Simulation
│   └── routers/
│       ├── alerts.py         # GET/POST /alerts + SSE + /simulate endpoints
│       ├── accounts.py       # Account DNA, trades, network graph
│       ├── reports.py        # PDF generation, weekly summary
│       ├── ps402.py          # ✅ 6 endpoints under /ps402 (incl. analyze-document)
│       └── mrfe.py           # ✅ 3 endpoints under /mrfe (text, file, status)
├── models/                   # All AI engines
│   ├── gnn/                  # Graph Neural Network (TCN)
│   │   ├── tcn.py
│   │   ├── train_tcn.py
│   │   ├── train_on_synthetic.py
│   │   └── tcn_weights.pt    # ✅ Trained (345 KB)
│   ├── dna/                  # Behavioral DNA Autoencoder
│   │   ├── autoencoder.py
│   │   ├── fingerprint_store.py
│   │   ├── train_on_synthetic.py
│   │   └── autoencoder_weights.pt  # ✅ Trained (341 KB)
│   ├── cross_market/         # Cross-market phantom fusion
│   │   └── fusion.py
│   ├── zero_day/             # Zero-day anomaly ensemble (IForest+LOF+HBOS+OCSVM)
│   │   └── anomaly.py
│   ├── misinfo/              # Financial misinformation classifier
│   │   ├── detector.py
│   │   ├── train_on_synthetic.py
│   │   └── misinfo_weights.pkl  # ✅ Auto-trained on first run
│   └── mrfe/                 # ✅ Market Reaction Fingerprint Engine (v2.1)
│       ├── __init__.py
│       └── engine.py         # analyze_text / analyze_pdf / analyze_document / fetch_historical
├── data/                     # Data ingestion & database
│   ├── db/
│   │   ├── models.py         # SQLAlchemy ORM — 7 tables incl. market_signals
│   │   ├── crud.py           # Full data access layer
│   │   └── session.py        # Smart PG/SQLite fallback, connection pooling
│   ├── ingest/
│   │   ├── nse_fetcher.py
│   │   ├── bse_fetcher.py
│   │   ├── sebi_scraper.py
│   │   ├── mca_fetcher.py
│   │   ├── broker_feed.py
│   │   ├── social_signal_fetcher.py   # Social media keyword + velocity scoring
│   │   ├── generic_threat_adapter.py  # Universal phishing/log/social normalizer
│   │   └── url_social_ingestor.py     # ✅ PS-402 URL & social post ingestion + DB
│   └── pipeline/
│       ├── cleaner.py        # Dedup, normalisation, validation
│       ├── kafka_producer.py
│       └── kafka_consumer.py
├── scoring/
│   ├── alert_engine.py       # Orchestrates 4 AI engines → weighted score → Alert
│   ├── impossibility.py      # Statistical impossibility boosters (×1.4–×1.8)
│   ├── mitigation_engine.py  # Severity + recommended_action + auto-mitigation
│   └── simulation_engine.py  # ✅ 5-scenario full-pipeline simulation (v2.1)
├── dashboard/                # Streamlit multi-page dashboard (Port 8501)
│   ├── app.py                # Navigation: 7 pages
│   ├── components/
│   └── pages/                # 7 pages
│       ├── live_alerts.py
│       ├── account_dna.py
│       ├── network_graph.py
│       ├── case_builder.py
│       ├── mitigation_center.py  # ✅ RUN SIMULATION panel + results table
│       ├── ps402_signals.py      # PS-402 digital threat signal page
│       └── mrfe_analysis.py      # ✅ MRFE Analysis page (text + file tabs)
├── argus-dashboard/          # [Legacy] React/Vite terminal dashboard (Port 5173)
│   └── src/
│       ├── App.jsx           # Router: 8 pages
│       ├── pages/            # 8 pages
│       │   ├── LiveAlerts.jsx
│       │   ├── AccountDNA.jsx
│       │   ├── NetworkView.jsx
│       │   ├── CaseBuilder.jsx
│       │   ├── WeeklySummary.jsx
│       │   ├── MitigationCenter.jsx  # ✅ RUN SIMULATION button + modal
│       │   ├── PS402Signals.jsx
│       │   └── MRFEAnalysis.jsx      # ✅ Text/file tabs + gauge + sparklines
│       ├── components/       # 12 reusable UI components
│       │   ├── AlertRow.jsx, CaseModal.jsx, LivePulse.jsx
│       │   ├── MetricCard.jsx, NetworkGraph.jsx, RadarChart.jsx
│       │   ├── SchemeBadge.jsx, ScoreBar.jsx, ScoreGauge.jsx
│       │   ├── Sidebar.jsx, ThreatBadge.jsx, TopBar.jsx
│       └── api/
│           └── client.js     # Axios + shape-normalisation adapter
├── argus-main/               # ✅ NEW — Next.js 16 + React 19 + TailwindCSS v4 dashboard (Port 3000)
│   ├── app/
│   │   ├── (dashboard)/
│   │   │   ├── alerts/           # Live Alerts page
│   │   │   ├── accounts/         # Account DNA page
│   │   │   ├── network/          # Network View page
│   │   │   ├── ps402/            # PS-402 Signals page
│   │   │   ├── analyzer/         # ✅ Document Threat Analyzer (drag-and-drop)
│   │   │   ├── cases/            # Case Builder page
│   │   │   ├── summary/          # Weekly Summary page
│   │   │   ├── mitigation/       # Mitigation Center page
│   │   │   └── reports/          # Reports page
│   │   └── globals.css           # TailwindCSS v4 global styles
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx       # Collapsible sidebar + engine status dots
│   │   │   ├── TopBar.tsx        # Top navigation bar
│   │   │   └── DashboardShell.tsx
│   │   ├── analyzer/
│   │   │   ├── upload-box.tsx    # Drag-and-drop file upload component
│   │   │   └── result-card.tsx   # Threat score result visualization
│   │   ├── ui/                   # shadcn/ui component library
│   │   ├── ps402/                # PS-402 signal components
│   │   └── reports/              # Report display components
│   ├── lib/
│   │   ├── api/
│   │   │   └── analyzer.ts       # analyzeDocument() → POST /ps402/analyze-document
│   │   └── mock/
│   │       └── mock-data.ts      # NAV_ITEMS, ENGINES, MOCK_ALERTS, ALERT_STATS
│   ├── store/                    # Global state
│   ├── types/
│   │   └── argus.ts              # Alert, NavItem, EngineInfo, EngineStatus types
│   ├── package.json              # Next 16.1.7, React 19.2.4, shadcn, tailwindcss v4
│   └── next.config.mjs
├── reports/
│   └── pdf_generator.py      # 8-section SEBI PDF + S3 upload → presigned URL
├── alembic/
│   ├── env.py                # POSTGRES_URL aware, batch mode enabled
│   └── versions/
│       ├── 001_initial.py    # All core tables
│       └── 002_market_signals.py  # market_signals table (dialect-agnostic)
├── infra/                    # AWS Infrastructure-as-Code
│   ├── DNS_SETUP.md          # Route 53 + external registrar instructions
│   └── terraform/            # 17 Terraform files
│       ├── main.tf, variables.tf, outputs.tf
│       ├── vpc.tf            # 3 public + 3 private subnets, IGW, NAT
│       ├── security_groups.tf
│       ├── ec2.tf, rds.tf, elasticache.tf
│       ├── s3.tf, iam.tf, ssm.tf
│       ├── alb.tf, route53.tf, cloudwatch.tf, ecr.tf
│       ├── userdata.sh       # cloud-init: Docker, CW agent, SSM secrets, cron
│       └── terraform.tfvars.example
├── .github/workflows/
│   ├── deploy.yml            # test → ECR build → SSM zero-SSH deploy
│   └── test.yml              # PR / branch test-only workflow
├── scripts/                  # 8 operational scripts
│   ├── prod_bootstrap.sh / .ps1   # One-command local production setup
│   ├── prod_stop.sh, prod_logs.sh
│   ├── db_backup.sh          # PostgreSQL pg_dump → S3
│   ├── aws_deploy.sh         # First-time Terraform + ECR push
│   ├── aws_update.sh         # Zero-downtime rolling restart on EC2
│   └── aws_backup.sh         # S3 model weights sync + RDS snapshot note
├── tests/                    # Pytest suite (4 modules)
├── demo/
│   ├── real_cases/           # 9 real case scenarios
│   │   ├── case_pump_dump.py
│   │   ├── case_circular_trading.py
│   │   ├── case_spoofing.py
│   │   ├── case_social_manipulation.py
│   │   ├── case_coordinated_botnet.py
│   │   ├── case_fake_news_campaign.py
│   │   ├── case_phishing_campaign.py
│   │   ├── case_platform_abuse.py
│   │   └── case_coordinated_botnet.py
│   ├── run_demo.py           # CLI runner for all cases
│   ├── synthetic_fraud.py    # Trade data generators
│   └── ps402_demo.py         # 5 PS-402 scenarios standalone
├── nginx/nginx.conf          # Reverse proxy + SSE passthrough + HTTPS-ready
├── docker-compose.yml        # Dev stack (6 services)
├── docker-compose.prod.yml   # Production stack (8 services: + worker + nginx)
├── docker-compose.aws.yml    # AWS overlay (removes self-hosted PG/Redis/Nginx)
├── Dockerfile.api            # Multi-stage, non-root user, uvloop, libpq5
├── Dockerfile.dashboard      # Multi-stage Node 20 → nginx:1.25 static serve
├── verify_argus.py           # ✅ 29-step full system verification suite
├── verify_sentinel.py        # SENTINEL-branded verify script
├── requirements.txt          # Python 3.11 deps incl. boto3, uvloop, pdfplumber
├── alembic.ini               # Alembic migration config
├── pyrightconfig.json        # VS Code type-checker config
├── pytest.ini                # asyncio_mode=auto
├── .env                      # Local dev secrets (never commit)
├── .env.example              # Safe template
├── .env.prod.example         # Production env template
└── argus_dev.db              # Auto-created SQLite DB (local dev)
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
| `pdfplumber` | 0.11.0 | PDF extraction for MRFE document analysis |
| `msgpack` | 1.0.8 | Binary serialization for Kafka messages |
| `boto3` | ≥1.34.0 | AWS SDK — S3 upload, SSM secrets, ECR |
| `uvloop` | ≥0.19.0 | High-performance asyncio event loop |

### `docker-compose.yml`
**Role:** Development convenience stack (6 services, no Nginx).

| Service | Image | Port | Role |
|---|---|---|---|
| `postgres` | postgres:16-alpine | 5432 | Primary database |
| `redis` | redis:7-alpine | 6379 | Caching & pub/sub |
| `zookeeper` | cp-zookeeper:7.5.0 | 2181 | Kafka coordinator |
| `kafka` | cp-kafka:7.5.0 | 9092 | Trade stream message broker |
| `argus-api` | Custom (Dockerfile.api) | 8000 | FastAPI + model server |
| `argus-dashboard` | Custom (Dockerfile.dashboard) | 5173 | React UI |

### `docker-compose.prod.yml`
**Role:** Hardened production stack — 8 services, named volumes, health checks, restart policies.

Adds `argus-worker` (Kafka consumer) and `nginx` (reverse proxy with SSE passthrough). All secrets from `.env.prod`. PostgreSQL data persisted via `postgres_data` named volume.

### `docker-compose.aws.yml`
**Role:** AWS overlay applied on top of `docker-compose.prod.yml`. Removes self-hosted `postgres`, `redis`, and `nginx` (replaced by RDS, ElastiCache, and ALB respectively) and switches all containers to the `awslogs` CloudWatch driver.

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.aws.yml up -d
```

### `Dockerfile.api`
**Role:** Container definition for the FastAPI API server and the Kafka worker. Uses Python 3.11 slim, installs requirements, and runs `uvicorn api.main:app` on port 8000.

### `Dockerfile.dashboard`
**Role:** Container definition for the React dashboard. Multi-stage build: Node 20 builds the Vite app, then nginx:1.25 serves the static bundle.

### `alembic.ini`
**Role:** Configuration for Alembic database migration tool. Points to the `alembic/` directory and the database URL.

### `pyrightconfig.json`
**Role:** Tells VS Code's Pylance/Pyright type-checker to look inside `.venv/` for installed packages, eliminating false "module not found" errors.

### `pytest.ini`
**Role:** Pytest configuration. Sets `asyncio_mode = auto` for async test support and `testpaths = tests/`.

### `argus_dev.db`
**Role:** SQLite database created automatically when running locally without PostgreSQL. In production, replaced by PostgreSQL.

### `verify_argus.py`
**Role:** ✅ **29-step** full system verification suite. Covers every component from DB init through MRFE, PDF analysis, and Simulation Engine.

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
  [PASS] MitigationEngine recommend() logic
  [PASS] MitigationEngine apply/dismiss/escalate (in-memory DB)
  [PASS] Mitigation endpoints registered on router
  [PASS] AlertOut + Mitigation schemas have all required fields
  [PASS] Social signal fetcher — pump text scoring
  [PASS] Misinfo detector — load weights + inference
  [PASS] Generic threat adapter — normalize() + normalize_batch()
  [PASS] ingest_url — phishing URL → signal_id + threat_score > 0
  [PASS] ingest_social_post — pump text → signal_id + RELIANCE in scrips
  [PASS] ps402 router registered — /ps402 prefix present on app
  [PASS] Health endpoint schema — status/backend/services/models/uptime_seconds
  [PASS] docker-compose.prod.yml — all required services present
  [PASS] nginx/nginx.conf — upstream/proxy_pass/SSE/ssl_certificate present
  [PASS] boto3 available for S3/SSM integration
  [PASS] docker-compose.aws.yml — aws overlay removes self-hosted DB/Redis
  [PASS] GitHub Actions deploy.yml — ECR build + SSM zero-SSH deploy present
  [PASS] MRFE analyze_text() — threat_score in [0,1], scrips list, event_type present
  [PASS] MRFE analyze_pdf() — pdf_pages >= 1, processing_time_ms >= 0
  [PASS] SimulationEngine pump_dump — status='pass', summary.passed >= 1 (in-memory SQLite)

Results: 29 PASSED  |  0 FAILED
========================================================
ARGUS is fully operational. 29/29 verified.
```

---

## API Layer (`api/`)

The API layer is a **FastAPI** application exposing all ARGUS functionality as a secured REST API with JWT authentication.

### `api/main.py`
**Role:** Application entry point. Registers 5 routers, configures CORS, and loads all 7 AI engines on startup via the `lifespan` async context manager.

**Engines loaded at startup:**
1. `tcn` — GNN/TCN coordination detector
2. `autoencoder` — Behavioral DNA autoencoder
3. `zero_day` — Zero-day anomaly ensemble
4. `fp_store` — Fraudster DNA fingerprint store
5. `mitigation_engine` — Severity + recommended_action engine
6. `misinfo_model` — TF-IDF misinformation classifier

**API title:** `SENTINEL — Digital Threat Detection API v2.0.0`

### `api/auth.py`
**Role:** Centralized JWT authentication dependency — extracted into its own module to prevent circular imports.

**Key components:**
- `JWT_SECRET` — loaded from env; signs all tokens
- `JWT_ALGORITHM` — HS256 (HMAC-SHA256)
- `oauth2_scheme` — FastAPI OAuth2 bearer token extractor
- `get_current_user(token)` — FastAPI dependency for all protected routes

### `api/schemas.py`
**Role:** All Pydantic v2 request/response schemas.

Key schema groups:
| Schema | Type | Used By |
|---|---|---|
| `TokenResponse` | Response | `POST /auth/token` |
| `HealthOut` | Response | `GET /health` |
| `AlertOut` | Response | All alert endpoints |
| `AlertStatusUpdate` | Request | `POST /alerts/{id}/status` body |
| `AlertAssign` | Request | `POST /alerts/{id}/assign` body |
| `MitigationApplyRequest` | Request | `POST /alerts/{id}/mitigate` |
| `MitigationDismissRequest` | Request | `POST /alerts/{id}/dismiss-mitigation` |
| `MitigationEscalateRequest` | Request | `POST /alerts/{id}/escalate` |
| `MitigationSummaryOut` | Response | `GET /alerts/mitigation/summary` |
| `PS402URLRequest` | Request | `POST /ps402/ingest/url` |
| `PS402SocialRequest` | Request | `POST /ps402/ingest/social` |
| `PS402BatchRequest` | Request | `POST /ps402/ingest/batch` |
| `MarketSignalOut` | Response | `GET /ps402/signals` |
| `MRFETextRequest` | Request | `POST /mrfe/analyze/text` |
| `MRFEAnalysisOut` | Response | MRFE endpoints |
| `SimulationRequest` | Request | `POST /alerts/simulate` |
| `SimulationResultOut` | Response | `POST /alerts/simulate` |

### `api/routers/alerts.py`
**Role:** All alert CRUD + mitigation lifecycle + SSE live stream + simulation.

Key endpoints:
- `GET /alerts` — Paginated alert list with filters (status, severity, mitigation_status, threat_type)
- `GET /alerts/live` — SSE real-time alert stream
- `GET /alerts/{id}` — Single alert with full detail
- `POST /alerts/{id}/status` — Update workflow status
- `POST /alerts/{id}/assign` — Assign to analyst
- `POST /alerts/{id}/mitigate` — Apply recommended mitigation
- `POST /alerts/{id}/dismiss-mitigation` — Dismiss recommendation
- `POST /alerts/{id}/escalate` — Escalate to SEBI
- `GET /alerts/mitigation/summary` — Aggregated mitigation statistics
- `GET /alerts/mitigation/pending` — Alerts pending action (filterable by severity)
- **`GET /alerts/simulate/scenarios`** — List 5+1 simulation scenarios
- **`POST /alerts/simulate`** — Run full pipeline simulation

### `api/routers/accounts.py`
- `GET /accounts/search` — Fuzzy account search
- `GET /accounts/{id}/dna` — DNA fingerprint + fraudster match
- `GET /accounts/{id}/trades` — Trade history (paginated)
- `GET /accounts/{id}/network` — 2-hop network graph

### `api/routers/reports.py`
- `POST /reports/case/{id}` — Generates a 8-page SEBI PDF; uploads to S3 if configured
- `GET /reports/case/{id}/download` — Download PDF (S3 presigned URL or local)
- `GET /reports/summary/weekly` — 7-day alert statistics

### `api/routers/ps402.py`
**PS-402 Digital Threat Ingestion layer (6 endpoints):**
- `POST /ps402/ingest/url` — Score a URL for phishing/threat + persist MarketSignal
- `POST /ps402/ingest/social` — Score a social post + persist MarketSignal
- `POST /ps402/ingest/batch` — Mixed batch of URLs + posts
- `GET /ps402/signals` — List market signals (filterable, paginated)
- `GET /ps402/summary` — 7-day digital threat summary stats
- **`POST /ps402/analyze-document`** ✅ **NEW v2.4** — Upload PDF/DOCX/TXT, extract text, run through PS-402 social pipeline + mitigation engine; returns `threat_score`, `misinfo_score`, `scrips_detected`, `is_malicious`, `severity`, `recommended_action`

### `api/routers/mrfe.py` ✅ v2.1
**Market Reaction Fingerprint Engine endpoints:**
- `POST /mrfe/analyze/text` — Analyze free-form text for financial threats
- `POST /mrfe/analyze/file` — Analyze uploaded file (PDF/TXT/CSV/DOCX, max 10 MB)
- `GET /mrfe/status` — Engine health + model availability (no auth required)

---

## AI Models (`models/`)

### `models/gnn/`
| File | Role |
|---|---|
| `tcn.py` | GAT model definition — 3-layer, 8-head attention, edge weight support |
| `train_tcn.py` | `load_model()` — loads from `tcn_weights.pt`, falls back to mock if missing |
| `train_on_synthetic.py` | Training script — run to retrain on fresh synthetic data |
| `tcn_weights.pt` | ✅ Pre-trained weights (345 KB, trained epoch 30) |

### `models/dna/`
| File | Role |
|---|---|
| `autoencoder.py` | LSTM encoder-decoder, `get_autoencoder()` — loads from `autoencoder_weights.pt` |
| `fingerprint_store.py` | Loads known fraudster DNA vectors; cosine-similarity matching |
| `train_on_synthetic.py` | Training script |
| `autoencoder_weights.pt` | ✅ Pre-trained weights (341 KB) |

### `models/cross_market/`
| File | Role |
|---|---|
| `fusion.py` | Correlation matrix + DoWhy causal inference; returns cross-market phantom score |

### `models/zero_day/`
| File | Role |
|---|---|
| `anomaly.py` | `get_detector()` — fits IForest+LOF+HBOS+OCSVM ensemble on sample data at startup |

### `models/misinfo/`
| File | Role |
|---|---|
| `detector.py` | `detect(text) → float` — TF-IDF + LR inference |
| `train_on_synthetic.py` | Trains and saves `misinfo_weights.pkl` |
| `misinfo_weights.pkl` | ✅ Auto-generated on first run |

### `models/mrfe/` ✅ v2.1
| File | Role |
|---|---|
| `__init__.py` | Package initializer |
| `engine.py` | `MRFEEngine` — `analyze_text()`, `analyze_pdf()`, `analyze_document()`, `fetch_historical()` |

---

## Data Layer (`data/`)

### `data/db/models.py`
SQLAlchemy ORM with **7 database tables**:

| Table | Key Columns |
|---|---|
| `trades` | account_id, scrip, exchange, timestamp, price, volume, side, is_manipulated |
| `entities` | name, type (individual/company/huf), mca_cin, related_entity_ids |
| `accounts` | id, broker, pan_hash, entity_id, behavioral_dna, is_flagged |
| `alerts` | 30+ columns: scrip, platform, impossibility_score, threat_category, severity, recommended_action, mitigation_status, auto_mitigated, escalated_to_sebi, misinfo_score, social_signal_score |
| `sebi_cases` | alert_id, case_number, entity_names, from_date, to_date, estimated_gain, evidence_json |
| `known_fraudsters` | entity_name, sebi_order_ref, behavioral_dna, scrips_involved |
| `market_signals` | signal_type, platform, source_url, raw_text, scrips_mentioned, misinfo_score, social_signal_score, threat_score, is_market_moving, alert_id |

**Dialect-agnostic:** `ARRAY` → `JSON` on SQLite, `PG_ARRAY` on PostgreSQL. `UUID` → `String(36)` on SQLite.

### `data/db/crud.py`
Complete data access layer — `get_alert`, `get_alerts`, `update_alert_status`, `assign_alert`, `count_alerts_today`, mitigation CRUD, PS-402 signal operations, and weekly summary aggregation.

### `data/db/session.py`
Smart session manager: tries `POSTGRES_URL` env first, falls back to SQLite `argus_dev.db`. Configures connection pooling (5 max, 10 overflow) for PostgreSQL; `check_same_thread=False` for SQLite.

### `data/ingest/`
| Module | Role |
|---|---|
| `nse_fetcher.py` | NSE bhavcopy + bulk deal data fetching |
| `bse_fetcher.py` | BSE equity data + announcements |
| `sebi_scraper.py` | SEBI enforcement orders + fraudster register |
| `mca_fetcher.py` | MCA21 company director & beneficial ownership data |
| `broker_feed.py` | Zerodha KiteConnect live trade feed adapter |
| `social_signal_fetcher.py` | Keyword + velocity scoring for pump signals |
| `generic_threat_adapter.py` | Universal normalizer: `normalize()`, `normalize_batch()` |
| `url_social_ingestor.py` | `ingest_url()`, `ingest_social_post()`, `ingest_batch()` — PS-402 core |

---

## Scoring Engine (`scoring/`)

### `scoring/alert_engine.py`
**Role:** Orchestration engine. Accepts a trade DataFrame, runs all 4 AI engines in sequence, applies the Poisson null model, computes the weighted composite score, and creates an `Alert` record if score ≥ threshold.

**Flow:** `trades_df → GNN → DNA → CrossMarket → ZeroDay → impossibility.py → composite → DB Alert`

### `scoring/impossibility.py`
**Role:** Applies multiplicative boosters to the raw composite score for mathematically impossible patterns. Returns the final `impossibility_score` on a 0–10 scale.

### `scoring/mitigation_engine.py`
**Role:** Assigns `severity` (critical/high/medium/low), `recommended_action`, and optionally applies `auto_mitigated=True` for critical threats.

**Actions available:**
- `freeze_accounts_and_escalate_sebi` — automatic for critical pump-and-dump/spoofing
- `freeze_accounts_pending_review`
- `flag_accounts_for_investigation`
- `block_social_signals_and_alert_compliance`
- `block_domain_and_alert_users` — automatic for phishing domains
- `flag_content_and_notify_exchange`
- `isolate_entity_and_escalate`
- `flag_entity_for_review`
- `monitor_and_log`

### `scoring/simulation_engine.py` ✅ v2.1
**Role:** Run 5 synthetic threat scenarios through the full ARGUS detection pipeline.

| Scenario | Description |
|---|---|
| `pump_dump` | 50 buy trades, 5 accounts, 3-hour window + MRFE pump text analysis |
| `spoofing` | 20 trades, 2 accounts, 30-minute window |
| `circular_trading` | 40 matched buy/sell pairs in ring formation, 5 accounts |
| `social_manipulation` | 20 synthetic pump posts → PS-402 signals |
| `phishing_campaign` | 3 spoofed URLs → generic threat adapter |

All results are labeled `synthetic_data_used: true`. Access via `POST /alerts/simulate`.

---

## Streamlit Dashboard (`dashboard/`)

**Port:** 8501 | **Pages:** 7

| Page | Module | Key Features |
|---|---|---|
| 🚨 Live Threat Alerts | `live_alerts.py` | Real-time alert table, severity filters, score bars, status actions |
| 🧬 Behavioral DNA | `account_dna.py` | DNA vector radar chart, fraudster match score, trade history |
| 🕸️ Threat Network | `network_graph.py` | pyvis network graph, account co-trading graph |
| 📁 Threat Report Builder | `case_builder.py` | SEBI PDF generation, download link |
| 🛡️ Mitigation Center | `mitigation_center.py` | ✅ **RUN SIMULATION** panel, pie charts, pending triage table |
| 🔍 PS-402 Signals | `ps402_signals.py` | Market signals table, threat heatmap |
| 🔬 MRFE Analysis | `mrfe_analysis.py` | ✅ Text/file tabs, metrics, Plotly sparklines, evidence snippets |

---

## Next.js Dashboard (`argus-main/`)

**Port:** 3000 | **Pages:** 9 | **Stack:** Next.js 16.1.7, React 19.2.4, TailwindCSS v4, shadcn/ui  
**Version:** v2.4.1 (shown in sidebar) | **Theme:** Dark zinc/cyan terminal aesthetic

The **primary pitch dashboard** — a modern, production-grade Next.js App Router frontend with server components, collapsible sidebar navigation, live engine status indicators, and full TypeScript typing.

| Page | Route | Key Features |
|---|---|---|
| Live Alerts | `/alerts` | Alert table with severity badges, score display |
| Account DNA | `/accounts` | DNA fingerprint visualization, fraudster matching |
| Network View | `/network` | Network graph explorer |
| PS-402 Signals | `/ps402` | Digital threat signals table |
| **Document Analyzer** | **`/analyzer`** | ✅ **Drag-and-drop upload** (PDF/DOCX/TXT), Run Threat Analysis button, `ResultCard` with scores + scrip list + mitigation action |
| Case Builder | `/cases` | SEBI PDF case generation |
| Weekly Summary | `/summary` | 7-day statistics |
| Mitigation Center | `/mitigation` | Mitigation triage dashboard |
| Reports | `/reports` | Report browsing and download |

**Key components:**
- `Sidebar` — Collapsible (60px / 240px) with engine status dots (GNN / DNA / Zero-Day / Cross-Mkt) and version badge
- `TopBar` — Session context and navigation controls
- `upload-box.tsx` — Drag-and-drop file zone for Document Analyzer
- `result-card.tsx` — Threat result display (scores, scrips detected, severity badge, recommended action)
- shadcn/ui component library (radix-ui primitives)

---

## Legacy React Dashboard (`argus-dashboard/`)

**Port:** 5173 | **Pages:** 8 | **Components:** 12 | **Theme:** Bloomberg Terminal (dark, monospace, cyan accent)

| Page | Route | Key Features |
|---|---|---|
| Live Alerts | `/alerts` | SSE real-time feed, ScoreGauge, AlertRow, scheme badges |
| Account DNA | `/dna` | RadarChart, DNA scores, fraudster similarity |
| Network Graph | `/network` | D3.js force-directed graph, 2-hop traversal |
| Case Builder | `/cases` | PDF generation, CaseModal, download |
| Weekly Summary | `/summary` | 7-day bar charts, trend lines |
| Digital Threats | `/ps402` | MarketSignals table, threat scores |
| Mitigation Center | `/mitigation` | ✅ Severity donut, action bars, **RUN SIMULATION** button + results modal |
| MRFE Analysis | `/mrfe` | ✅ Text/file drag-drop tabs, ScoreGauge, impact badge, sparklines |

**Key components:**
- `AlertRow` — Color-coded alert rows with scheme badge, score bar, action buttons
- `ScoreGauge` — Circular SVG gauge (0–10) with color zones
- `MetricCard` — KPI metric with label and delta
- `Sidebar` — Collapsible nav with SYSTEM STATUS live dots
- `ThreatBadge` — Impact level badge (low/medium/high/critical)

---

## Reports (`reports/`)

### `reports/pdf_generator.py`
**Role:** Generates SEBI-compliant 8-page case PDFs using ReportLab.

**Report sections:**
1. Executive Summary
2. Alert Metadata (scrip, timestamp, composite score)
3. AI Engine Score Breakdown (bar chart)
4. Network Graph Evidence
5. Trade Timeline Analysis
6. Entity Profile
7. Recommended Action
8. Case Signing Block (officer name, date)

**S3 Integration:** If `AWS_REGION` and `S3_REPORTS_BUCKET` are set, the PDF is uploaded and a presigned URL (7-day expiry) is returned alongside the local path.

---

## Database Migrations (`alembic/`)

| Version | File | Creates |
|---|---|---|
| `001_initial` | `001_initial.py` | `trades`, `entities`, `accounts`, `alerts`, `sebi_cases`, `known_fraudsters` tables |
| `002_market_signals` | `002_market_signals.py` | `market_signals` table (dialect-agnostic JSON arrays) |

```bash
alembic upgrade head   # Apply all pending migrations
alembic downgrade -1   # Roll back one version
```

---

## Tests (`tests/`)

Pytest-based test suite with `asyncio_mode=auto`. Covers FastAPI routes via `httpx.AsyncClient`, alert engine scoring, mitigation logic, and PS-402 ingestion.

```bash
pytest tests/ -v
```

---

## Demo (`demo/`)

### Real Cases (`demo/real_cases/`) — 9 scenarios

| File | Scheme | Coverage |
|---|---|---|
| `case_pump_dump.py` | Pump & Dump | GNN + Zero-Day + Social Signal |
| `case_circular_trading.py` | Circular Trading | GNN + DNA |
| `case_spoofing.py` | Spoofing/Layering | GNN |
| `case_social_manipulation.py` | Social Manipulation | Social Signal + Misinfo |
| `case_coordinated_botnet.py` | Coordinated Bot Attack | GNN + Social |
| `case_fake_news_campaign.py` | Fake News Campaign | Misinfo + PS-402 |
| `case_phishing_campaign.py` | Phishing Campaign | Generic Threat Adapter + PS-402 |
| `case_platform_abuse.py` | Platform Abuse | PS-402 + Social Signal |
| `case_coordinated_botnet.py` | Multi-platform botnet | GNN + Cross-Market |

### `demo/ps402_demo.py`
5 standalone PS-402 scenario demonstrations (no API server required).

### `demo/run_demo.py`
CLI runner:
```bash
python demo/run_demo.py --case pump_dump
python demo/run_demo.py --case all
```

---

## Infrastructure (`infra/`)

### Terraform (`infra/terraform/`) — 17 files

| File | Provisions |
|---|---|
| `main.tf` | AWS provider, backend config skeleton |
| `variables.tf` | All input variables (region, domain, instance type, etc.) |
| `vpc.tf` | VPC, 3 public + 3 private subnets, IGW, NAT gateway, route tables |
| `security_groups.tf` | SGs for ALB, EC2, RDS, ElastiCache |
| `ec2.tf` | t3.xlarge, EIP, key pair, userdata template |
| `rds.tf` | RDS PostgreSQL 16, encrypted, 7-day automated backups |
| `elasticache.tf` | ElastiCache Redis 7, TLS, AUTH token |
| `s3.tf` | 2 S3 buckets: reports + model weights (versioned, lifecycle rules) |
| `iam.tf` | EC2 instance role: S3/ECR/SSM/CloudWatch permissions |
| `ssm.tf` | 7 secrets in Parameter Store (DB URL, Redis URL, JWT secret, admin PW, etc.) |
| `alb.tf` | Application Load Balancer, ACM certificate, HTTP→HTTPS, SSE sticky rule |
| `route53.tf` | A records + ACM DNS validation CNAME |
| `cloudwatch.tf` | 5 log groups, 6 alarms (5xx, latency, CPU, storage), multi-widget dashboard |
| `ecr.tf` | `argus-api` + `argus-dashboard` container registries |
| `outputs.tf` | ALB DNS, EC2 IP, RDS endpoint, S3 URLs, SSM session command |
| `userdata.sh` | cloud-init: Docker install, CloudWatch agent, pull SSM secrets, start stack, cron |
| `terraform.tfvars.example` | Safe-to-commit variable template |

### GitHub Actions (`.github/workflows/`)

| Workflow | File | Trigger |
|---|---|---|
| Deploy | `deploy.yml` | `push` to `main` |
| Tests | `test.yml` | All PRs + branches |

**Deploy workflow stages:**
1. **Test** — `pytest tests/`
2. **Build** — ECR login → `docker build` API + Dashboard images → `docker push`
3. **Deploy** — SSM `run-command` on EC2: `docker compose pull && docker compose up -d` (zero-SSH)

---

## Database Schema

### `alerts` table (key columns)

| Column | Type | Description |
|---|---|---|
| `id` | UUID/String | Primary key |
| `scrip` | String | Entity/target identifier (ticker or URL/domain) |
| `platform` | String | twitter / reddit / telegram / web / email / other |
| `exchange` | String | Legacy alias for platform |
| `detected_at` | DateTime | UTC timestamp of detection |
| `impossibility_score` | Float | 0–10 composite threat score |
| `threat_category` | String | coordinated_attack / malicious_content / phishing / misinformation / platform_abuse / novel_threat |
| `scheme_type` | String | Legacy alias for threat_category |
| `entities_involved` | JSON/Array | Entity IDs or usernames |
| `accounts_involved` | JSON/Array | Legacy alias |
| `gnn_score` | Float | Coordination detection score (0–1) |
| `dna_score` | Float | Behavioral anomaly score (0–1) |
| `cross_market_score` | Float | Cross-platform signal score (0–1) |
| `zero_day_score` | Float | Novelty/unknown threat score (0–1) |
| `social_signal_score` | Float | Social manipulation signal (0–1) |
| `misinfo_score` | Float | Misinformation probability (0–1) |
| `threat_type` | String | market_manipulation / social_media_threat / misinformation / phishing / generic_digital_threat |
| `status` | Enum | open / investigating / closed / false_positive |
| `severity` | String | critical / high / medium / low |
| `recommended_action` | String | freeze_accounts / block_domain / monitor / etc. |
| `mitigation_status` | String | pending / applied / dismissed / escalated |
| `auto_mitigated` | Boolean | True if system auto-applied action |
| `escalated_to_sebi` | Boolean | True if escalated to regulator |
| `content_sample` | Text | Flagged post/URL/message snippet |

### `market_signals` table

| Column | Type | Description |
|---|---|---|
| `id` | String(36) | UUID primary key |
| `signal_type` | String | url_threat / social_post / news_headline / whatsapp_forward |
| `platform` | String | twitter / reddit / telegram / web / whatsapp |
| `source_url` | String | Original URL if available |
| `raw_text` | Text | Post body / headline |
| `scrips_mentioned` | JSON | `["XYZLTD", "ABCBANK"]` |
| `entity_id` | String | Account/user if known |
| `misinfo_score` | Float | 0–1 |
| `social_signal_score` | Float | 0–1 |
| `threat_score` | Float | 0–1 composite |
| `is_market_moving` | Boolean | True if threat_score ≥ 0.60 |
| `alert_id` | String(36) | FK → alerts.id (if alert created) |
| `ingested_at` | DateTime | UTC ingest timestamp |
| `source_meta` | JSON | likes, shares, velocity, domain metadata |

---

## PS-402 Ingestion API

The PS-402 layer connects the SENTINEL API to the digital threat ingestion pipeline.

### Ingest a URL
```http
POST /ps402/ingest/url
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "http://nse1ndia-login.xyz",
  "platform": "web",
  "submitted_by": "analyst_01"
}
```

**Response:**
```json
{
  "signal_id": "8f3b...",
  "threat_score": 0.72,
  "is_market_moving": true,
  "alert_id": "a4c2...",
  "platform": "web",
  "ingested_at": "2026-04-10T12:00:00Z"
}
```

### Ingest a Social Post
```http
POST /ps402/ingest/social
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "RELIANCE going to 500% — operator call — buy NOW!!",
  "platform": "reddit",
  "scrips": ["RELIANCE"]
}
```

### Batch Ingest
```http
POST /ps402/ingest/batch
Authorization: Bearer <token>
Content-Type: application/json

{
  "records": [
    {"type": "url", "url": "http://sebi-fake.xyz", "platform": "web"},
    {"type": "social", "text": "ZEE pump alert!", "platform": "twitter"}
  ]
}
```

---

## Document Threat Analyzer

**New in v2.4** — End-to-end document threat analysis via upload.

### Backend: `POST /ps402/analyze-document`

Accepts PDF, DOCX, or TXT file uploads via `multipart/form-data`. Internally:
1. Extracts text using `pdfplumber` (PDF), `python-docx` (DOCX), or direct decode (TXT)
2. Runs extracted text through `ingest_social_post()` — the PS-402 social pipeline (misinfo detector + social signal fetcher + generic threat adapter)
3. Scores misinformation probability (`misinfo_score`) and overall threat level (`threat_score`)
4. Queries `MitigationEngine.recommend()` for a severity + `recommended_action`
5. Returns JSON with detection results

```http
POST /ps402/analyze-document
Authorization: Bearer <token>
Content-Type: multipart/form-data

file=@suspect_doc.pdf
```

**Response:**
```json
{
  "filename": "suspect_doc.pdf",
  "threat_score": 0.74,
  "misinfo_score": 0.68,
  "threat_type": "misinformation",
  "scrips_detected": ["RELIANCE", "XYZLTD"],
  "is_malicious": true,
  "severity": "high",
  "recommended_action": "flag_content_and_notify_exchange"
}
```

| Field | Type | Description |
|---|---|---|
| `filename` | string | Original uploaded filename |
| `threat_score` | float [0–1] | Combined PS-402 threat signal |
| `misinfo_score` | float [0–1] | Financial misinformation probability |
| `threat_type` | string | `misinformation` / `generic_digital_threat` / `low_risk_document` |
| `scrips_detected` | list[str] | NSE scrip tickers extracted from document |
| `is_malicious` | bool | `true` if `threat_score ≥ 0.60` |
| `severity` | string | `critical` / `high` / `medium` / `low` |
| `recommended_action` | string | Mitigation action from MitigationEngine |

### Frontend: Document Analyzer page (`/analyzer`)

Located at `argus-main/app/(dashboard)/analyzer/page.tsx`. Features:
- **`UploadBox`** — Drag-and-drop zone for PDF/DOCX/TXT files
- **Run Threat Analysis** button — disabled until file selected, shows spinner during analysis
- **`ResultCard`** — Displays all 7 response fields with color-coded severity badge
- **Error handling** — Shows API error messages inline
- **Reset flow** — "Analyze another" link clears state for next document

API integration via `argus-main/lib/api/analyzer.ts` → `analyzeDocument(file)` → `POST /ps402/analyze-document`.

---

## Data Sources

| Source | Module | Data Type |
|---|---|---|
| NSE Bhavcopy | `nse_fetcher.py` | End-of-day OHLCV, delivery data |
| BSE Equity Data | `bse_fetcher.py` | OHLCV, corporate announcements |
| SEBI Enforcement Orders | `sebi_scraper.py` | Fraudster register, penalty orders |
| MCA21 | `mca_fetcher.py` | Company directors, beneficial ownership |
| Zerodha KiteConnect | `broker_feed.py` | Real-time tick data, order book |
| Social Media (simulated) | `social_signal_fetcher.py` | Twitter, Reddit, WhatsApp signals |
| Phishing URLs | `generic_threat_adapter.py` | URL threat intelligence |
| Live Trade Stream | `kafka_consumer.py` | Kafka-based real-time trades |

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
| GET | `/alerts` | ✅ | List alerts (paginated; filter by status/severity/mitigation_status) |
| GET | `/alerts/live` | ✅ | SSE real-time alert stream |
| GET | `/alerts/{id}` | ✅ | Single alert detail |
| POST | `/alerts/{id}/status` | ✅ | Update status |
| POST | `/alerts/{id}/assign` | ✅ | Assign to analyst |
| POST | `/alerts/{id}/mitigate` | ✅ | Apply recommended mitigation action |
| POST | `/alerts/{id}/dismiss-mitigation` | ✅ | Dismiss mitigation recommendation |
| POST | `/alerts/{id}/escalate` | ✅ | Escalate alert to SEBI enforcement |
| GET | `/alerts/mitigation/summary` | ✅ | Aggregated mitigation statistics |
| GET | `/alerts/mitigation/pending` | ✅ | List alerts pending mitigation (filterable by severity) |
| **GET** | **`/alerts/simulate/scenarios`** | ❌ | **List 5 simulation scenarios** |
| **POST** | **`/alerts/simulate`** | ✅ | **Run full pipeline simulation** |
| GET | `/accounts/search` | ✅ | Search accounts |
| GET | `/accounts/{id}/dna` | ✅ | Behavioral DNA + fraudster match |
| GET | `/accounts/{id}/trades` | ✅ | Trade history |
| GET | `/accounts/{id}/network` | ✅ | 2-hop network graph |
| POST | `/reports/case/{id}` | ✅ | Generate SEBI PDF case |
| GET | `/reports/case/{id}/download` | ✅ | Download PDF |
| GET | `/reports/summary/weekly` | ✅ | 7-day statistics |
| **POST** | **`/ps402/ingest/url`** | ✅ | **PS-402: Ingest & score a URL** |
| **POST** | **`/ps402/ingest/social`** | ✅ | **PS-402: Ingest & score a social post** |
| **POST** | **`/ps402/ingest/batch`** | ✅ | **PS-402: Batch ingest mixed records** |
| **GET** | **`/ps402/signals`** | ✅ | **PS-402: List market signals with filters** |
| **GET** | **`/ps402/summary`** | ✅ | **PS-402: 7-day digital threat summary** |
| **POST** | **`/mrfe/analyze/text`** | ✅ | **MRFE: Analyze text for financial threats** |
| **POST** | **`/mrfe/analyze/file`** | ✅ | **MRFE: Analyze uploaded PDF/TXT/CSV/DOCX (max 10 MB)** |
| **GET** | **`/mrfe/status`** | ❌ | **MRFE: Engine status & model availability** |
| **POST** | **`/ps402/analyze-document`** | ✅ | **PS-402: Upload PDF/DOCX/TXT → threat + misinfo scores + mitigation action** |

**Total: 32 endpoints** across 5 routers.

---

## Quick Start — Local Dev

**Prerequisites:** Python 3.11, Git

```bash
# 1. Enter project directory
cd "d:\Argus for LR\ARGUS-for-LR"

# 2. Activate virtual environment
.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt

# 4. Verify the full system (29/29 must pass)
python verify_argus.py

# 5. Start the API server
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# 6. Open Swagger UI
# http://127.0.0.1:8000/docs

# 7. Login credentials
# Username: admin  |  Password: argus2024

# 8. Start Streamlit dashboard (separate terminal)
streamlit run dashboard/app.py

# 9. Start Next.js dashboard — primary pitch UI (separate terminal)
cd "d:\Argus for LR\argus-main"
npm install
npm run dev
# http://localhost:3000

# 10. [Optional] Start legacy Vite/React dashboard (separate terminal)
cd argus-dashboard
npm install
npm run dev
# http://localhost:5173
```

### Common Commands

```bash
# Run all demos
python demo/run_demo.py --case all

# Run a specific demo
python demo/run_demo.py --case pump_dump

# Run PS-402 standalone demo
python demo/ps402_demo.py

# Seed the database with realistic test data
python demo/synthetic_fraud.py

# Run simulation via CLI (API must be running)
curl -X POST http://localhost:8000/alerts/simulate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "all"}'

# Analyze text via MRFE API
curl -X POST http://localhost:8000/mrfe/analyze/text \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"text": "XYZLTD guaranteed 500% returns operator call"}'

# Run database migrations
alembic upgrade head

# Run test suite
pytest tests/ -v
```

---

## Docker Deployment

### Development Stack

```bash
docker compose up -d
```

- API: http://localhost:8080
- Dashboard: http://localhost:5173
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### Production Stack

```bash
# Using bash
bash scripts/prod_bootstrap.sh

# Using PowerShell
.\scripts\prod_bootstrap.ps1

# Manual
docker compose -f docker-compose.prod.yml up -d
```

All services: PostgreSQL 16, Redis 7, Zookeeper, Kafka, argus-api, argus-worker, argus-dashboard, nginx

### Nginx

Configured as reverse proxy at port 80/443. Routes:
- `/` → React dashboard (port 5173)
- `/api/` → FastAPI (port 8000)
- `/alerts/live` → SSE passthrough (buffering disabled, long timeout)
- `/reports/` → PDF download passthrough

---

## AWS Deployment

### Architecture

```
Internet → Route 53 → ALB (HTTPS/ACM) → EC2 t3.xlarge
                                          ├── argus-api (Docker)
                                          └── argus-dashboard (Docker)
                                          ↕
                              RDS PostgreSQL 16 (private subnet)
                              ElastiCache Redis 7 (private subnet)
                              S3 (reports + model weights)
```

### First-Time Deployment

```bash
# 1. Fill in Terraform variables
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
# Edit terraform.tfvars with your domain, key pair, region, etc.

# 2. Deploy infrastructure + application
bash scripts/aws_deploy.sh
```

The script:
1. Runs `terraform init && terraform apply`
2. Builds and pushes Docker images to ECR
3. Uses SSM RunCommand to start the stack on EC2 (zero SSH required)

### Updating the Application

```bash
# Push to main — GitHub Actions auto-deploys
git push origin main

# Or manually trigger update on EC2
bash scripts/aws_update.sh
```

### Key AWS Resources

| Resource | Type | Purpose |
|---|---|---|
| EC2 t3.xlarge | Compute | Docker host for API + Dashboard |
| RDS PostgreSQL 16 | Database | Primary DB (Multi-AZ optional) |
| ElastiCache Redis 7 | Cache | Session cache + pub/sub |
| S3 (two buckets) | Storage | PDF reports + model weight backups |
| ALB + ACM | Load Balancer + TLS | HTTPS termination + routing |
| Route 53 | DNS | Custom domain A records |
| CloudWatch | Monitoring | Logs, alarms (5xx, latency, CPU, storage) |
| ECR (two repos) | Container Registry | argus-api + argus-dashboard images |
| SSM Parameter Store | Secrets | 7 secret parameters (no plaintext in code) |

### DNS Setup

See `infra/DNS_SETUP.md` for Route 53 + external registrar configuration steps.

### Security Notes

- **Never commit** `terraform.tfvars`, `.env`, `.env.prod`
- All secrets stored in **SSM Parameter Store** — pulled by `userdata.sh` at instance launch
- EC2 accessed via **SSM Session Manager** (zero open SSH port)
- RDS and ElastiCache are in **private subnets** — not accessible from the internet
- ALB terminates TLS; ACM certificates are **auto-renewed**

### Backup & Recovery

```bash
# Manual S3 model weight backup + RDS snapshot note
bash scripts/aws_backup.sh

# PostgreSQL dump to S3
bash scripts/db_backup.sh
```

---

## Current Status

**As of April 2026 — Fully Operational — 29/29 Verified**

| Component | Status | Notes |
|---|---|---|
| **GNN / TCN Engine** | ✅ Operational | Trained weights loaded (345 KB), AUC-ROC validated |
| **DNA Autoencoder** | ✅ Operational | Trained weights loaded (341 KB), fraudster matching active |
| **Cross-Market Detector** | ✅ Operational | DoWhy causal inference + correlation matrix |
| **Zero-Day Ensemble** | ✅ Operational | IForest + LOF + HBOS + OCSVM fitted at startup |
| **Social Signal Fetcher** | ✅ Operational | Keyword + velocity scoring for pump signals |
| **Misinfo Detector** | ✅ Operational | TF-IDF + LR, weights auto-loaded on first inference |
| **Generic Threat Adapter** | ✅ Operational | Phishing / transaction / activity log normalizer |
| **URL & Social Ingestor** | ✅ Operational | `url_social_ingestor.py` — PS-402 ingestion, scoring, DB persistence, alert creation |
| **Mitigation Engine** | ✅ Operational | severity + recommended_action + auto_mitigate on every alert; 5 API endpoints |
| **MRFE Engine** | ✅ NEW v2.1 | Multi-format threat analyzer (text/PDF/CSV/DOCX); 3 endpoints |
| **Simulation Engine** | ✅ NEW v2.1 | 5 synthetic scenarios through full pipeline; `POST /alerts/simulate` |
| **Scoring Engine** | ✅ Upgraded | Poisson null model + impossibility boosters + supplementary scores |
| **FastAPI API** | ✅ Running | Port 8000, JWT auth, SSE live stream, **32 endpoints** across 5 routers |
| **Next.js Dashboard** | ✅ NEW v2.4 | Port 3000, **9 pages** incl. Document Analyzer; Next.js 16 + React 19 + TailwindCSS v4 |
| **Streamlit Dashboard** | ✅ Running | Port 8501, **7 pages** incl. MRFE Analysis + Simulation panel |
| **Legacy React Dashboard** | ✅ Running | Port 5173, **8 pages**, 12 components, MRFE Analysis + Sim modal |
| **Document Threat Analyzer** | ✅ NEW v2.4 | `POST /ps402/analyze-document` — PDF/DOCX/TXT upload → threat score + mitigation |
| **SEBI PDF Generator** | ✅ Working | 8-page case reports with evidence tables |
| **SQLite DB** | ✅ Active | `market_signals` table + 30+ columns on `alerts` table |
| **Alembic Migrations** | ✅ 2 versions | `001_initial` + `002_market_signals` |
| **Demo Scenarios** | ✅ Live | 9 real-case demos + `ps402_demo.py` (5/5 PASS) + 5-scenario simulation |
| **Verification Suite** | ✅ **29/29 PASSED** | `verify_argus.py` — all 29 checks pass |
| **torch-geometric** | 2.5.3 | Installed and verified importable |
| **pyod** | 1.1.3 | Required by Zero-Day Ensemble |
| **Dockerfile.api** | ✅ Production | Multi-stage build, non-root user, uvloop, libpq5 |
| **Dockerfile.dashboard** | ✅ Production | Multi-stage Node 20 → nginx:1.25 static serve |
| **docker-compose.prod** | ✅ 8 services | postgres(16), redis(7), zookeeper, kafka, api, worker, dashboard, nginx — health checks + named volumes |
| **Nginx** | ✅ Configured | Reverse proxy, SSE passthrough, PDF download, HTTPS-ready skeleton |
| **Scripts** | ✅ 8 scripts | prod + aws bootstrap/update/backup/logs/stop |
| **Terraform IaC** | ✅ 17 files | VPC, EC2, RDS PostgreSQL 16, ElastiCache Redis 7, S3, ALB, Route53, CloudWatch, ECR, SSM, IAM |
| **GitHub Actions** | ✅ CI/CD | Test suite → ECR build → SSM zero-SSH deploy on every `main` push |
| **AWS S3 integration** | ✅ Operational | PDF reports + model weights with presigned URLs; boto3 verified |
| **CloudWatch** | ✅ Configured | 5 log groups, 6 alarms (5xx, latency, CPU, storage), multi-widget dashboard |

**Functional highlights:**
- **Document Threat Analyzer (v2.4)**: NEW — `POST /ps402/analyze-document` accepts PDF/DOCX/TXT uploads, extracts text, scores via PS-402 pipeline, recommends mitigation. Matching Next.js page at `/analyzer` with drag-and-drop UI and `ResultCard` visualization.
- **PS-402 Ingestion Layer**: Full URL and social post ingestion pipeline — `ingest_url()`, `ingest_social_post()`, `ingest_batch()` — with phishing heuristics, misinfo scoring, velocity boost, `MarketSignal` DB persistence, and automatic `Alert` creation when `threat_score ≥ 0.60`.
- **8-Engine + Mitigation Architecture**: GNN, DNA, Cross-Market, Zero-Day, Social Signal, Misinfo Detector, URL/Social Ingestor, **MRFE Engine**, and Real-Time Mitigation Engine all operational.
- **Triple Dashboard (9+8+7 pages)**: Next.js 16 primary UI with Document Analyzer; React has MRFE Analysis + Sim modal + Digital Threats; Streamlit has MRFE Analysis + PS-402 Signals + Simulation panel.
- **MRFE Engine (v2.1)**: Analyzes text, PDF, TXT, CSV, DOCX for financial threats — heuristic threat scoring, event classification, scrip extraction, 30-day price context.
- **Simulation Engine (v2.1)**: 5 synthetic scenarios (pump_dump, spoofing, circular_trading, social_manipulation, phishing_campaign) through full detection pipeline.
- **Trained Models**: GNN (345 KB), DNA autoencoder (341 KB), and Misinfo classifier have saved weights; all load at API startup in < 1 second.
- **Real-Time Mitigation**: Every new alert gets `severity`, `recommended_action`, `auto_mitigated`, and `escalated_to_sebi` populated at creation time.
- **Auto-Mitigation**: Critical pump-and-dump/spoofing alerts and phishing threats are auto-acted without analyst intervention.
- **9 Real-Case Demos**: pump_dump, circular_trading, spoofing, social_manipulation, coordinated_botnet, fake_news_campaign, phishing_campaign, platform_abuse, plus `ps402_demo` (5/5 PASS).
- **Offline Demo Mode**: Next.js and React dashboards both support mock data for pitch presentations without a live API.
- **PDF Reports**: SEBI-compliant 8-page case PDFs generate successfully.
- **Windows-Safe**: All Unicode/emoji print statements replaced with ASCII equivalents; `charmap` codec errors eliminated.

---

## Known Limitations

1. **Synthetic Training Data**: GNN and DNA models trained on synthetic patterns — not real SEBI enforcement case data. Accuracy on novel real-world schemes is unknown.

2. **MRFE Heuristic Scoring**: MRFE threat scores are heuristic composites, not statistically calibrated classifiers. Do not use exact percentages as accuracy claims.

3. **Social Media Mocking**: The social signal fetcher simulates API calls — actual Twitter/Reddit/Telegram API keys not included. In production, wire real API clients.

4. **No KYC Integration**: Account behavioral DNA depends on trade history. New accounts with < 10 trades cannot be profiled accurately.

5. **Redis Optional**: Redis pub/sub is gracefully degraded — runs without it (SSE still works via polling). For production, Redis is strongly recommended.

6. **Kafka Optional**: Kafka consumer is not required for API startup. AlertEngine accepts DataFrames directly for testing.

7. **PDF Extraction Limits**: MRFE PDF analysis uses `pdfplumber` — encrypted PDFs and scanned-image PDFs are not supported.

8. **Windows Compatibility**: `uvloop` is a Linux-only asyncio speedup. On Windows, the standard asyncio loop is used (functionally equivalent).

---

## Roadmap

### Done ✅
- [x] 4-engine composite scoring (GNN + DNA + Cross-Market + Zero-Day)
- [x] PS-402 digital threat ingestion (URL + social post + batch)
- [x] Full mitigation lifecycle (apply / dismiss / escalate / auto-mitigate)
- [x] SEBI PDF case reports with S3 upload + presigned URL
- [x] Dual dashboards: React (8 pages) + Streamlit (7 pages)
- [x] Docker Compose dev + production + AWS overlay stacks
- [x] Terraform IaC for full AWS deployment (17 files)
- [x] GitHub Actions CI/CD (zero-SSH ECR → SSM deploy)
- [x] MRFE Engine — multi-format document threat analyzer (v2.1)
- [x] Simulation Engine — 5-scenario full pipeline demo (v2.1)
- [x] `verify_argus.py` **29/29 PASSED**
- [x] **Document Threat Analyzer (v2.4)** — `POST /ps402/analyze-document` + Next.js `/analyzer` page with drag-and-drop upload and `ResultCard` visualization
- [x] **Next.js 16 Dashboard (v2.4)** — Primary pitch UI (`argus-main/`) with 9 pages, React 19, TailwindCSS v4, shadcn/ui, collapsible sidebar with engine status dots

### Planned 🔜
- [ ] Real-time Kafka consumer integration for live trade stream
- [ ] MFA / role-based access control (analyst vs. admin vs. read-only)
- [ ] ECS Fargate migration for granular container auto-scaling
- [ ] MRFE accuracy calibration on labeled real-world financial threat corpus
- [ ] WebSocket upgrade for React live alert stream (replace SSE)
- [ ] Alerting integrations: Slack, PagerDuty, SEBI email webhook
- [ ] Historical pattern backtest runner across archived NSE/BSE data
- [ ] Model retraining pipeline with periodic data refresh
- [ ] Connect Next.js dashboard to live FastAPI backend (currently mock data)
- [ ] Docker image for `argus-main` Next.js frontend

---

*SENTINEL — Scalable ENTity Intelligence for NEtwork-Level threat detection*  
*Built for the NEOFuture Hackathon PS-402: Detection of Digital Threats & Malicious Content*  
*v2.4.1 — April 2026: Document Threat Analyzer, Next.js 16 dashboard, 32 API endpoints, 29/29 verification suite.*  
*AWS production deploy: Terraform IaC (17 files), GitHub Actions CI/CD, S3 PDF/model storage, RDS PostgreSQL 16, ElastiCache Redis 7, CloudWatch monitoring.*
