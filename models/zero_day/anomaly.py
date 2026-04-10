"""
models/zero_day/anomaly.py — Zero-Day Scheme Detector using PyOD ensemble.
Detects never-before-seen manipulation patterns via unsupervised anomaly detection.
"""
from __future__ import annotations

import os
import pickle
import numpy as np
import pandas as pd
from typing import Optional
from scipy.stats import ks_2samp, expon


ENSEMBLE_PATH = os.path.join(os.path.dirname(__file__), "ensemble.pkl")
N_FEATURES = 25


class ZeroDayDetector:
    """
    Ensemble anomaly detector: IForest + LOF + HBOS + OCSVM.
    Score per sample is the mean normalized anomaly score across all models (0–10).
    """

    def __init__(self):
        self._models: Optional[list] = None

    def _build_models(self) -> list:
        from pyod.models.iforest import IForest
        from pyod.models.lof import LOF
        from pyod.models.hbos import HBOS

        return [
            IForest(contamination=0.05, n_estimators=50, random_state=42, n_jobs=1),
            LOF(n_neighbors=min(10, 5), contamination=0.05, n_jobs=1),
            HBOS(n_bins=10, contamination=0.05),
        ]

    def fit(self, normal_feature_matrix: np.ndarray) -> None:
        """
        Fits all 4 models on normal (clean) feature matrix.
        Saves ensemble to ENSEMBLE_PATH.
        """
        if normal_feature_matrix.shape[0] < 10:
            return

        X = np.nan_to_num(normal_feature_matrix, nan=0.0, posinf=10.0, neginf=-10.0)
        # Normalize
        self._mean = X.mean(axis=0)
        self._std = X.std(axis=0) + 1e-9
        X_norm = (X - self._mean) / self._std

        self._models = self._build_models()
        for model in self._models:
            try:
                model.fit(X_norm)
            except Exception:
                pass

        with open(ENSEMBLE_PATH, "wb") as f:
            pickle.dump({"models": self._models, "mean": self._mean, "std": self._std}, f)

    def score(self, feature_matrix: np.ndarray) -> np.ndarray:
        """
        Returns normalized ensemble anomaly score per sample (0–10).
        Higher = more anomalous.
        """
        if self._models is None:
            self.load()

        if self._models is None or feature_matrix.shape[0] == 0:
            return np.zeros(feature_matrix.shape[0])

        X = np.nan_to_num(feature_matrix, nan=0.0, posinf=10.0, neginf=-10.0)
        if hasattr(self, "_mean"):
            X = (X - self._mean) / self._std

        all_scores = []
        for model in self._models:
            try:
                raw_scores = model.decision_function(X)
                # Normalize to [0, 1]
                s_min, s_max = raw_scores.min(), raw_scores.max()
                if s_max - s_min > 1e-9:
                    normalized = (raw_scores - s_min) / (s_max - s_min)
                else:
                    normalized = np.zeros_like(raw_scores)
                all_scores.append(normalized)
            except Exception:
                all_scores.append(np.zeros(len(X)))

        ensemble_score = np.mean(all_scores, axis=0)
        return (ensemble_score * 10.0).clip(0, 10)

    def load(self) -> "ZeroDayDetector":
        """Loads fitted ensemble from disk."""
        if os.path.exists(ENSEMBLE_PATH):
            with open(ENSEMBLE_PATH, "rb") as f:
                data = pickle.load(f)
            self._models = data["models"]
            self._mean = data.get("mean", 0.0)
            self._std = data.get("std", 1.0)
        else:
            self._models = self._build_models()
            self._mean = 0.0
            self._std = 1.0
        return self

    def build_session_features(
        self,
        trades_df: pd.DataFrame,
        window_minutes: int = 30,
    ) -> np.ndarray:
        """
        Aggregates trades into window_minutes windows, computes 25 statistical features per window.
        Returns feature matrix of shape (n_windows, 25).
        """
        if trades_df.empty:
            return np.zeros((1, N_FEATURES), dtype=np.float32)

        df = trades_df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")

        df = df.dropna(subset=["timestamp"])
        if df.empty:
            return np.zeros((1, N_FEATURES), dtype=np.float32)

        df["window"] = df["timestamp"].dt.floor(f"{window_minutes}min")

        feature_rows = []
        for window, grp in df.groupby("window"):
            feats = _compute_window_features(grp)
            feature_rows.append(feats)

        if not feature_rows:
            return np.zeros((1, N_FEATURES), dtype=np.float32)

        return np.array(feature_rows, dtype=np.float32)


def _compute_window_features(grp: pd.DataFrame) -> list[float]:
    """Computes 25 statistical features from a window of trades."""
    vol = grp["volume"] if "volume" in grp.columns else pd.Series([1.0])
    price = grp["price"] if "price" in grp.columns else pd.Series([100.0])
    side = grp["side"] if "side" in grp.columns else pd.Series(["BUY"])
    acc = grp["account_id"] if "account_id" in grp.columns else pd.Series(["x"])
    ts = grp["timestamp"]

    ts_ms = ts.astype(np.int64) // 1_000_000
    inter_arrivals = np.diff(sorted(ts_ms.values)).astype(float)
    if len(inter_arrivals) == 0:
        inter_arrivals = np.array([1.0])
    inter_arrivals = np.abs(inter_arrivals) + 1e-9

    # 1. trade_count
    f1 = float(len(grp))
    # 2. volume_total
    f2 = float(vol.sum())
    # 3. volume_entropy
    vol_norm = vol / (vol.sum() + 1e-9)
    f3 = float(-np.sum(vol_norm * np.log(vol_norm + 1e-9)))
    # 4. price_mean
    f4 = float(price.mean())
    # 5. price_std
    f5 = float(price.std()) if len(price) > 1 else 0.0
    # 6. price_autocorr
    f6 = float(price.autocorr(lag=1)) if len(price) > 2 else 0.0
    # 7. order_imbalance
    n_buy = float((side == "BUY").sum())
    n_sell = float((side == "SELL").sum())
    f7 = abs(n_buy - n_sell) / (f1 + 1e-9)
    # 8. buy_ratio
    f8 = n_buy / (f1 + 1e-9)
    # 9. unique_accounts
    f9 = float(acc.nunique())
    # 10. accounts_per_trade
    f10 = f9 / (f1 + 1e-9)
    # 11. avg_inter_arrival_ms
    f11 = float(inter_arrivals.mean())
    # 12. std_inter_arrival_ms
    f12 = float(inter_arrivals.std()) if len(inter_arrivals) > 1 else 0.0
    # 13. cv_inter_arrival (coefficient of variation)
    f13 = f12 / (f11 + 1e-9)
    # 14. trade_clustering_coeff (ratio of trades in tightest 10% time window)
    sorted_ts = np.sort(ts_ms.values)
    if len(sorted_ts) > 1:
        total_span = max(sorted_ts[-1] - sorted_ts[0], 1)
        window_10pct = total_span * 0.1
        cluster_count = sum(1 for i in range(1, len(sorted_ts)) if sorted_ts[i] - sorted_ts[i-1] <= window_10pct)
        f14 = cluster_count / (f1 + 1e-9)
    else:
        f14 = 0.0
    # 15. inter_arrival KS-test vs exponential (p-value; low = non-exponential)
    try:
        exp_sample = np.random.exponential(scale=float(inter_arrivals.mean()), size=len(inter_arrivals))
        _, ks_p = ks_2samp(inter_arrivals, exp_sample)
        f15 = float(ks_p)
    except Exception:
        f15 = 1.0
    # 16. inter_arrival KS-test vs Pareto
    try:
        pareto_sample = np.random.pareto(a=1.5, size=len(inter_arrivals)) * float(inter_arrivals.min())
        _, ks_pareto_p = ks_2samp(inter_arrivals, pareto_sample)
        f16 = float(ks_pareto_p)
    except Exception:
        f16 = 1.0
    # 17. price_range_pct
    f17 = float((price.max() - price.min()) / (price.mean() + 1e-9) * 100) if len(price) > 0 else 0.0
    # 18. price_momentum
    f18 = float(price.diff().mean() or 0.0)
    # 19. vol_concentration (Herfindahl index)
    vol_by_acc = grp.groupby("account_id")["volume"].sum() if "account_id" in grp.columns else vol
    shares = vol_by_acc / (vol_by_acc.sum() + 1e-9)
    f19 = float((shares ** 2).sum())
    # 20. max_single_account_pct
    f20 = float(shares.max()) if len(shares) > 0 else 0.0
    # 21. scrip_diversity
    f21 = float(grp["scrip"].nunique()) if "scrip" in grp.columns else 1.0
    # 22. evening_trade_ratio
    f22 = float((ts.dt.hour >= 15).mean())
    # 23. opening_trade_ratio
    f23 = float((ts.dt.hour == 9).mean())
    # 24. large_trade_ratio
    f24 = float((vol > vol.quantile(0.9)).mean()) if len(vol) > 1 else 0.0
    # 25. price_direction_consistency
    diffs = price.diff().dropna()
    f25 = float((diffs > 0).mean()) if len(diffs) > 0 else 0.5

    return [
        f1, f2, f3, f4, f5, f6, f7, f8, f9, f10,
        f11, f12, f13, f14, f15, f16, f17, f18, f19, f20,
        f21, f22, f23, f24, f25,
    ]


_global_detector: Optional[ZeroDayDetector] = None


def get_detector() -> ZeroDayDetector:
    """Returns the cached global ZeroDayDetector, loading from disk if needed."""
    global _global_detector
    if _global_detector is None:
        _global_detector = ZeroDayDetector().load()
    return _global_detector
