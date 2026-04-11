"""
models/finbert/sentiment.py — FinBERT financial sentiment analysis.

Uses ProsusAI/finbert (HuggingFace) to classify financial text as:
  positive | negative | neutral

The model is loaded lazily on first use and cached in memory.
Falls back gracefully if transformers is not installed or the model
cannot be downloaded (returns neutral/0.5 so the pipeline stays live).
"""
from __future__ import annotations

import logging
from typing import TypedDict

logger = logging.getLogger(__name__)

# ── Types ─────────────────────────────────────────────────────────────────────

class FinBERTResult(TypedDict):
    label: str          # "positive" | "negative" | "neutral"
    score: float        # confidence in [0, 1]
    negative_prob: float  # normalised P(negative) used for threat scoring


# ── Singleton pipeline ─────────────────────────────────────────────────────────

_pipeline = None
_AVAILABLE = None          # None = untested, True/False after first call


def _get_pipeline():
    global _pipeline, _AVAILABLE
    if _AVAILABLE is False:
        return None
    if _pipeline is not None:
        return _pipeline
    try:
        import os
        # Force HuggingFace to use PyTorch — avoids keras/__internal__ error
        # when TensorFlow is partially installed.
        os.environ.setdefault("USE_TORCH", "1")
        os.environ.setdefault("USE_TF", "0")
        from transformers import pipeline as hf_pipeline
        logger.info("FinBERT: loading ProsusAI/finbert …")
        _pipeline = hf_pipeline(
            "text-classification",
            model="ProsusAI/finbert",
            top_k=None,          # return all three labels
            truncation=True,
            max_length=512,
            framework="pt",      # explicitly PyTorch
        )
        _AVAILABLE = True
        logger.info("FinBERT: model loaded successfully.")
        return _pipeline
    except Exception as exc:
        logger.warning("FinBERT unavailable (%s). Falling back to heuristics.", exc)
        _AVAILABLE = False
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def analyse(text: str, max_chars: int = 3000) -> FinBERTResult:
    """
    Run FinBERT on `text` and return a FinBERTResult dict.

    Truncates to `max_chars` to stay within the 512 token limit.
    If the model is unavailable, returns a neutral fallback result.
    """
    if not text or not text.strip():
        return {"label": "neutral", "score": 1.0, "negative_prob": 0.0}

    pipe = _get_pipeline()
    if pipe is None:
        return {"label": "neutral", "score": 0.5, "negative_prob": 0.1}

    try:
        snippet = text[:max_chars]
        raw = pipe(snippet)
        # raw is a list-of-lists when top_k=None: [[{label, score}, ...]]
        scores_list = raw[0] if isinstance(raw[0], list) else raw

        label_map: dict[str, float] = {
            item["label"].lower(): item["score"] for item in scores_list
        }

        # Normalise label names (FinBERT may return "POSITIVE" etc.)
        neg_prob  = label_map.get("negative", 0.0)
        pos_prob  = label_map.get("positive", 0.0)
        neu_prob  = label_map.get("neutral",  0.0)

        # Best label
        best = max(label_map, key=label_map.get)   # type: ignore[arg-type]
        best_score = label_map[best]

        return {
            "label":         best,
            "score":         round(best_score, 4),
            "negative_prob": round(neg_prob, 4),
        }
    except Exception as exc:
        logger.warning("FinBERT.analyse() failed: %s", exc)
        return {"label": "neutral", "score": 0.5, "negative_prob": 0.1}


def is_available() -> bool:
    """Return True if FinBERT loaded successfully."""
    _get_pipeline()
    return _AVAILABLE is True
