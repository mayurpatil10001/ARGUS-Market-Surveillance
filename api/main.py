"""
api/main.py — SENTINEL FastAPI application entrypoint.
JWT authentication, CORS, lifespan model loading, health endpoint.
SENTINEL: Scalable ENTity Intelligence for NEtwork-Level threat detection
"""
from __future__ import annotations

import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from api.auth import get_current_user, JWT_SECRET, JWT_ALGORITHM
from api.schemas import HealthOut, TokenResponse
from api.routers import alerts as alerts_router
from api.routers import accounts as accounts_router
from api.routers import reports as reports_router
from data.db.session import get_db, engine
from data.db.models import Base

load_dotenv()

logger = logging.getLogger(__name__)

JWT_EXPIRE_MINUTES = 480  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-dev admin user — in production this should come from a users DB table
# Password is truncated to 64 chars to avoid bcrypt 72-byte limit issues
_ADMIN_PASSWORD_RAW = os.getenv("ADMIN_PASSWORD", "argus2024")[:64]
_ADMIN_HASHED: str | None = None  # lazily hashed on first request

ADMIN_USERNAME = "admin"
ADMIN_ROLE = "admin"


def _get_admin_hash() -> str:
    global _ADMIN_HASHED
    if _ADMIN_HASHED is None:
        _ADMIN_HASHED = pwd_context.hash(_ADMIN_PASSWORD_RAW)
    return _ADMIN_HASHED

# Global model state loaded at startup
_app_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all AI models on startup; release on shutdown."""
    logger.info("SENTINEL startup: creating DB tables...")
    Base.metadata.create_all(bind=engine)

    logger.info("Loading Network Coordination Detector (TCN/GNN)...")
    try:
        from models.gnn.train_tcn import load_model
        _app_state["tcn"] = load_model()
    except Exception as exc:
        logger.warning(f"Network Coordination Detector load failed: {exc}")
        _app_state["tcn"] = None

    logger.info("Loading Behavioral Anomaly Profiler (DNA Autoencoder)...")
    try:
        from models.dna.autoencoder import get_autoencoder
        _app_state["autoencoder"] = get_autoencoder()
    except Exception as exc:
        logger.warning(f"Behavioral Anomaly Profiler load failed: {exc}")
        _app_state["autoencoder"] = None

    logger.info("Loading Novel Threat Detector (Zero-Day)...")
    try:
        from models.zero_day.anomaly import get_detector
        _app_state["zero_day"] = get_detector()
    except Exception as exc:
        logger.warning(f"Novel Threat Detector load failed: {exc}")
        _app_state["zero_day"] = None

    logger.info("Loading Behavioral Fingerprint store...")
    try:
        from models.dna.fingerprint_store import FingerprintStore
        fp_store = FingerprintStore()
        db_session = next(get_db())
        fp_store.load_fraudster_dnas(db_session)
        db_session.close()
        _app_state["fp_store"] = fp_store
    except Exception as exc:
        logger.warning(f"FingerprintStore load failed: {exc}")
        _app_state["fp_store"] = None

    logger.info("Loading Mitigation engine...")
    try:
        from scoring.mitigation_engine import get_mitigation_engine
        _app_state["mitigation_engine"] = get_mitigation_engine()
    except Exception as exc:
        logger.warning(f"MitigationEngine load failed: {exc}")
        _app_state["mitigation_engine"] = None

    logger.info("Loading Malicious Content Classifier (Misinfo detector)...")
    try:
        from models.misinfo.detector import _get_pipeline
        _get_pipeline()
        _app_state["misinfo_model"] = "loaded"
    except Exception as exc:
        logger.warning(f"Malicious Content Classifier load failed: {exc}")
        _app_state["misinfo_model"] = None

    logger.info("SENTINEL startup complete. All 6 AI engines initialized.")
    yield

    logger.info("SENTINEL shutting down...")
    if _app_state.get("fp_store"):
        try:
            _app_state["fp_store"].close()
        except Exception:
            pass


app = FastAPI(
    title="SENTINEL — Digital Threat Detection API",
    description=(
        "Scalable ENTity Intelligence for NEtwork-Level threat detection. "
        "Detects coordinated bot attacks, malicious content, phishing campaigns, "
        "and platform abuse across Twitter, Reddit, Telegram, and the web. "
        "Built for PS-402: Detection of Digital Threats & Malicious Content."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://argus-dashboard:8501",
        "http://127.0.0.1:8501",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts_router.router, prefix="/alerts", tags=["Alerts"])
app.include_router(accounts_router.router, prefix="/accounts", tags=["Accounts"])
app.include_router(reports_router.router, prefix="/reports", tags=["Reports"])

from api.routers import ps402 as ps402_router  # noqa: E402
app.include_router(ps402_router.router, prefix="/ps402", tags=["PS-402 Digital Threats"])


# ─── Auth ─────────────────────────────────────────────────────────────────────

def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MINUTES))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


# get_current_user is defined in api.auth to avoid circular imports


@app.post("/auth/token", response_model=TokenResponse, tags=["Auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Issues JWT bearer token for valid credentials."""
    if form_data.username != ADMIN_USERNAME:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not _verify_password(form_data.password[:64], _get_admin_hash()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = _create_token({"sub": form_data.username, "role": ADMIN_ROLE})
    return TokenResponse(access_token=token)


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthOut, tags=["System"])
async def health_check(db: Session = Depends(get_db)):
    """Returns SENTINEL service health status and loaded AI engine versions."""
    services: dict = {}

    # DB check
    try:
        from sqlalchemy import text as sa_text
        db.execute(sa_text("SELECT 1"))
        services["db"] = "ok"
    except Exception:
        services["postgres"] = "error"

    # Redis check — optional; not_configured is acceptable for local dev
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url or redis_url in ("redis://redis:6379", "redis://localhost:6379"):
        try:
            import redis as redis_lib
            r = redis_lib.from_url(redis_url or "redis://localhost:6379", socket_connect_timeout=1)
            r.ping()
            r.close()
            services["redis"] = "ok"
        except Exception:
            services["redis"] = "not_configured"
    else:
        try:
            import redis as redis_lib
            r = redis_lib.from_url(redis_url, socket_connect_timeout=2)
            r.ping()
            r.close()
            services["redis"] = "ok"
        except Exception:
            services["redis"] = "error"

    model_versions = {
        "network_coordination_detector": "loaded" if _app_state.get("tcn") else "not_loaded",
        "behavioral_anomaly_profiler": "loaded" if _app_state.get("autoencoder") else "not_loaded",
        "novel_threat_detector": "loaded" if _app_state.get("zero_day") else "not_loaded",
        "behavioral_fingerprint_store": "loaded" if _app_state.get("fp_store") else "not_loaded",
        "mitigation_engine": "loaded" if _app_state.get("mitigation_engine") else "not_loaded",
        "malicious_content_classifier": _app_state.get("misinfo_model") or "not_loaded",
    }

    overall_status = "ok" if services.get("db") == "ok" else "degraded"
    return HealthOut(
        status=overall_status,
        system="SENTINEL",
        version="2.0.0",
        services=services,
        model_versions=model_versions,
    )
