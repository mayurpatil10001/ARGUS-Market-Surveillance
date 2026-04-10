"""
models/misinfo/detector.py — Financial Misinformation Detector.
TF-IDF + Logistic Regression classifier trained on synthetic labeled data.
Detects fake financial news, pump language, unverified insider claims, etc.
"""
from __future__ import annotations

import logging
import os
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent / "misinfo_weights.pkl"

# ── Singleton cache ───────────────────────────────────────────────────────────
_cached_pipeline = None


def _get_pipeline():
    """Load or return cached TF-IDF + LR pipeline."""
    global _cached_pipeline
    if _cached_pipeline is not None:
        return _cached_pipeline

    if _MODEL_PATH.exists():
        try:
            with open(_MODEL_PATH, "rb") as f:
                _cached_pipeline = pickle.load(f)
            logger.info("MisinfoDetector: loaded weights from disk.")
            return _cached_pipeline
        except Exception as exc:
            logger.warning(f"MisinfoDetector: weight load failed ({exc}), training inline.")

    # Train inline from synthetic data
    from models.misinfo.train_on_synthetic import build_pipeline
    _cached_pipeline = build_pipeline(save=True)
    return _cached_pipeline


def detect(text: str) -> float:
    """
    Detect financial misinformation / manipulation in text.

    Parameters
    ----------
    text : str
        Raw social media post, news headline, or financial content.

    Returns
    -------
    float
        Probability in [0, 1] that the text is misinformation/manipulation.
        0 = legitimate content, 1 = certain misinformation.
    """
    if not text or not text.strip():
        return 0.0
    try:
        pipeline = _get_pipeline()
        proba = pipeline.predict_proba([text])[0]
        # proba[1] = P(misinformation)
        return float(round(proba[1], 4))
    except Exception as exc:
        logger.warning(f"MisinfoDetector.detect() failed: {exc}")
        return 0.0


def detect_batch(texts: list[str]) -> list[float]:
    """Batch detect on multiple texts. Returns list of probabilities."""
    if not texts:
        return []
    try:
        pipeline = _get_pipeline()
        probas = pipeline.predict_proba(texts)
        return [float(round(p[1], 4)) for p in probas]
    except Exception as exc:
        logger.warning(f"MisinfoDetector.detect_batch() failed: {exc}")
        return [0.0] * len(texts)


def reload():
    """Force reload the model from disk (e.g. after retraining)."""
    global _cached_pipeline
    _cached_pipeline = None
    return _get_pipeline()
