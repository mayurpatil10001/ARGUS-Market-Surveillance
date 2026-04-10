"""
models/dna/fingerprint_store.py — Redis-backed DNA fingerprint store with known fraudster matching.
"""
from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np
import redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
DNA_TTL_SECONDS = 30 * 24 * 3600  # 30 days
FRAUDSTER_KEY_PREFIX = "argus:fraudster_dna:"
ACCOUNT_KEY_PREFIX = "argus:account_dna:"
FRAUDSTER_INDEX_KEY = "argus:fraudster_index"


class FingerprintStore:
    """
    Redis-backed store for behavioral DNA fingerprints.
    Supports fast cosine similarity lookup against known fraudsters.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self._client = redis.from_url(redis_url or REDIS_URL, decode_responses=False)
        self._fraudster_cache: dict[str, tuple[np.ndarray, dict]] = {}

    def store(self, account_id: str, dna: np.ndarray) -> None:
        """Stores account DNA fingerprint in Redis with 30-day TTL."""
        key = f"{ACCOUNT_KEY_PREFIX}{account_id}"
        payload = json.dumps(dna.tolist()).encode("utf-8")
        self._client.set(key, payload, ex=DNA_TTL_SECONDS)

    def get(self, account_id: str) -> Optional[np.ndarray]:
        """Retrieves account DNA fingerprint. Returns None if not found."""
        key = f"{ACCOUNT_KEY_PREFIX}{account_id}"
        raw = self._client.get(key)
        if raw is None:
            return None
        return np.array(json.loads(raw.decode("utf-8")), dtype=np.float32)

    def store_fraudster(self, fraudster_id: str, dna: np.ndarray, meta: dict) -> None:
        """Stores a known fraudster DNA with metadata."""
        key = f"{FRAUDSTER_KEY_PREFIX}{fraudster_id}"
        payload = json.dumps({"dna": dna.tolist(), "meta": meta}).encode("utf-8")
        self._client.set(key, payload)
        self._client.sadd(FRAUDSTER_INDEX_KEY, fraudster_id)
        # Update local cache
        self._fraudster_cache[fraudster_id] = (dna, meta)

    def load_fraudster_dnas(self, session) -> int:
        """
        Loads all KnownFraudster records with non-null behavioral_dna into Redis.
        Returns count of fraudsters loaded.
        """
        from data.db.crud import get_all_known_fraudsters

        fraudsters = get_all_known_fraudsters(session)
        loaded = 0
        for fr in fraudsters:
            if fr.behavioral_dna and len(fr.behavioral_dna) > 0:
                dna = np.array(fr.behavioral_dna, dtype=np.float32)
                meta = {
                    "entity_name": fr.entity_name,
                    "sebi_order_ref": fr.sebi_order_ref,
                    "scheme_type": fr.scheme_type,
                    "scrips_involved": fr.scrips_involved or [],
                    "conviction_date": str(fr.conviction_date),
                }
                self.store_fraudster(str(fr.id), dna, meta)
                loaded += 1
        return loaded

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Computes cosine similarity between two vectors."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def find_similar(
        self,
        dna: np.ndarray,
        threshold: float = 0.85,
    ) -> list[dict]:
        """
        Finds known fraudsters whose DNA is cosine-similar to the given DNA.
        Checks local cache first, then loads from Redis if cache is empty.
        Returns list of dicts: {fraudster_id, similarity, entity_name, scheme_type, ...}
        """
        if not self._fraudster_cache:
            self._load_cache_from_redis()

        matches = []
        for frid, (fdna, meta) in self._fraudster_cache.items():
            sim = self._cosine_similarity(dna, fdna)
            if sim >= threshold:
                matches.append({
                    "fraudster_id": frid,
                    "similarity": round(sim, 4),
                    **meta,
                })

        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches

    def _load_cache_from_redis(self) -> None:
        """Loads all fraudster DNA entries from Redis into local cache."""
        try:
            fids = self._client.smembers(FRAUDSTER_INDEX_KEY)
            for fid in fids:
                fid_str = fid.decode("utf-8") if isinstance(fid, bytes) else fid
                key = f"{FRAUDSTER_KEY_PREFIX}{fid_str}"
                raw = self._client.get(key)
                if raw:
                    data = json.loads(raw.decode("utf-8"))
                    dna = np.array(data["dna"], dtype=np.float32)
                    self._fraudster_cache[fid_str] = (dna, data["meta"])
        except Exception:
            pass

    def close(self) -> None:
        self._client.close()
