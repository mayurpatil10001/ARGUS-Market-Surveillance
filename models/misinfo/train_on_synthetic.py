"""
models/misinfo/train_on_synthetic.py — Train & save misinformation classifier.
Generates synthetic labeled data internally, trains TF-IDF + LogisticRegression,
and saves the pipeline to models/misinfo/misinfo_weights.pkl.

Run standalone:
    python models/misinfo/train_on_synthetic.py
"""
from __future__ import annotations

import logging
import os
import pickle
import sys
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_PATH = Path(__file__).parent / "misinfo_weights.pkl"

# ── Synthetic training data ───────────────────────────────────────────────────

_LEGITIMATE = [
    "Reliance Industries Q3 results beat analyst estimates; net profit up 12% YoY.",
    "SEBI issues circular on mutual fund exposure limits to alternative investment funds.",
    "RBI keeps repo rate unchanged at 6.5%; monetary policy stance remains withdrawal of accommodation.",
    "TCS reports 4.5% growth in consolidated revenue for Q4 FY24.",
    "Infosys revises FY24 revenue guidance upward to 1.0-3.5% in constant currency.",
    "HDFC Bank's net interest margin contracts slightly due to rising deposit costs.",
    "NSE and BSE jointly release quarterly derivatives turnover statistics.",
    "ONGC discovers new hydrocarbon reserves in KG basin; stock gains 2%.",
    "Maruti Suzuki reports record sales of 1.78 lakh units in March 2024.",
    "ITC's cigarette business faces volume headwinds amid excise hike proposals.",
    "Wipro announces share buyback at Rs 500 per share; board approves Rs 2,500 crore program.",
    "The markets closed marginally lower today amid global cues and profit booking.",
    "SEBI proposes stricter disclosure norms for foreign portfolio investors.",
    "Bajaj Finance Q4 AUM growth at 34% YoY; asset quality stable.",
    "Government increases minimum support price for kharif crops by 5-8%.",
    "Federal Reserve signals fewer rate cuts in 2024; FII outflows expected from EMs.",
    "Coal India production rises 10% in FY24; target of 1 billion tonnes set for FY27.",
    "Titan Company's jewellery segment sees robust quarter with 20% revenue growth.",
    "NTPC commissions 500 MW solar capacity in Rajasthan; renewable portfolio expands.",
    "Axis Bank's net NPA ratio improves to 0.31%; credit costs remain benign.",
    "Cipla receives USFDA approval for generic drug; stock rallies on the news.",
    "Tech Mahindra deal wins momentum in BFSI vertical; Europe revenues improve.",
    "Sun Pharma's specialty business in US delivers strong sequential growth.",
    "Asian Paints volume growth moderate due to channel inventory correction.",
    "BPCL reports refinery throughput of 9.5 MMT in Q4 FY24.",
    "Quarterly results season underway; analysts expect single-digit earnings growth.",
    "Indian economy grew 8.4% in Q3 FY24; full year target of 7.6% intact.",
    "FIIs turned net buyers in April 2024 as domestic macros remain supportive.",
    "SEBI tightens rules on algorithmic trading; consultation paper released.",
    "NSE launches new derivative products on commodity indices.",
    "Portfolio analysis shows diversification benefits in current volatile environment.",
    "Index rebalancing will add three new constituents to Nifty 50 in June.",
    "Mutual fund SIP inflows hit record Rs 20,000 crore in March 2024.",
    "IRDAI issues new guidelines on insurance product mis-selling.",
    "Sensex crosses 75,000 for the first time on strong domestic investor participation.",
]

_MISINFO = [
    "🚀 XYZTECH going to MOON! 100x returns guaranteed! Buy before 9:15 AM! Join t.me/pump_group",
    "INSIDER TIP: RELIANCE buyback at Rs 3000 confirmed. Load up NOW! SEBI approved deal.",
    "Hidden gem alert: SMALLCAP123 operator move. Price target 500%. No risk guaranteed profit!",
    "FIIs buying XYZTECH in BULK secretly. This is the next multibagger. Get in before circuit!",
    "URGENT: Government awarded Rs 50,000 crore contract to NEWSTOCK. Share before deleted!",
    "DEMOBROADCAST going parabolic! Strong accumulation. Upper circuit target today. FOMO NOW",
    "Join our PAID GROUP for 200% returns in 2 weeks. Price target before Monday open!",
    "SEBI approved breakout in GEMSTOCK. Promoters loading aggressively. Last chance to buy!",
    "Insider info: TECHCO acquisition confirmed at 300% premium. Buy before announcement!",
    "PIPEDREAM stock operator move detected. Load 1000 shares before 10 AM sure shot target.",
    "Direct tip from promoter: XYZ results will beat by 500%. Buy now risk free money doubling!",
    "🔥 HOTSTOCK circuit upper 20% guaranteed today. Join our WhatsApp group for free signals!",
    "Breaking: RBI backing CRYPTOSTOCK project. First govt blockchain currency. Buy now 1000x",
    "Coordinated buy: 500 members buying PUMPCO at 9:15. Join discord.gg/pumpgroup to sync.",
    "INSIDER: PHARMASTOCK US FDA approval coming TONIGHT. Price will 5x by morning guaranteed.",
    "🚨 ALERT: MANIP stock delivery based manipulation pattern. 400% in 3 days confirmed!",
    "Buy SCAMCO before promoter announces buyback tomorrow. Confirmed source. Limited time only!",
    "HIDDEN GEM: undervalued company FAKESTOCK about to get SEBI approved mega fund injection.",
    "This stock is going to explode! 10 big operators loading. Price target 300% in a week!",
    "Secret bulk deal happening in TINYSTOCK. Get in at Rs 10 target Rs 50. Guaranteed move.",
    "PUMP ALERT: coordinated buying in INFLATE stock 3 PM. Get in before circuit hits.",
    "Direct from operator: BIGMOVE stock going upper circuit for 5 days. God guarantee.",
    "Breaking: Tata Group acquiring SMALLCO at 250% premium. Buy immediately before news breaks!",
    "Free tip: LUCKYSTOCK inside info — results 1000% beat coming. Join Telegram for full alert.",
    "🚀 XYZTECH Social Media Campaign: 10,000 members buying at open. To the moon! Share now!",
    "WARNING DELETE AFTER READING: MONEYBAG operator loading. Upper circuit locked. Join now!",
    "FAKE SEBI ORDER: Trading suspended for REALSTOCK due to regulatory probe. Sell immediately!",
    "Coordinated pump: All members buy SYNTHSTOCK at exactly 10:30 AM for guaranteed circuit.",
    "Unverified: BIGBANK announcing merger tomorrow at 8 PM. Price will 3x before exchange opens.",
    "PUMP GROUP ALERT: 20 brokers coordinating buy in INFLATED stock. Join before 9:00 AM!",
    "GUARANTEED: MEMESTOCK will hit upper circuit for 10 consecutive days. God promise profit!",
    "Secret WhatsApp group: 1000 members loading PUMPSTOCK. Be part of The next big move!",
    "INSIDER GROUP: Buy XYZTECH before Adani Group announcement. 100% confirmed source.",
    "BREAKING FAKE NEWS: SBIN declaring special dividend of Rs 500. Buy before market opens!",
    "Circuit stock PROFITCO will hit 20% upper circuit five days in row. God guarantee!",
]

# ── Augmentation helpers ──────────────────────────────────────────────────────

def _augment(texts: list[str], rng: np.random.Generator, n: int = 3) -> list[str]:
    """Simple augmentation: shuffle words, add noise phrases."""
    noise_prefix = [
        "BREAKING: ", "URGENT! ", "🔥 ", "⚠️ ", "ALERT: ", "EXCLUSIVE: ",
    ]
    augmented = list(texts)
    for _ in range(n):
        for t in texts:
            words = t.split()
            if len(words) > 5:
                # Random word swap
                i, j = rng.integers(0, len(words), size=2)
                words[i], words[j] = words[j], words[i]
            aug = " ".join(words)
            # Optionally prepend noise prefix
            if rng.random() < 0.3:
                aug = rng.choice(noise_prefix) + aug
            augmented.append(aug)
    return augmented


def build_pipeline(save: bool = True):
    """
    Build and optionally save a TF-IDF + LogisticRegression pipeline.

    Returns the fitted sklearn Pipeline.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.model_selection import cross_val_score

    rng = np.random.default_rng(42)

    # Augment data
    legit_aug = _augment(_LEGITIMATE, rng, n=4)
    misinfo_aug = _augment(_MISINFO, rng, n=6)

    X = legit_aug + misinfo_aug
    y = [0] * len(legit_aug) + [1] * len(misinfo_aug)

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 3),
            max_features=8000,
            min_df=1,
            sublinear_tf=True,
            strip_accents="unicode",
        )),
        ("clf", LogisticRegression(
            C=1.0,
            class_weight="balanced",
            max_iter=500,
            solver="lbfgs",
            random_state=42,
        )),
    ])

    pipeline.fit(X, y)

    # Quick cross-val log
    try:
        cvscores = cross_val_score(pipeline, X, y, cv=3, scoring="f1")
        logger.info(f"MisinfoDetector CV F1: {cvscores.mean():.3f} ± {cvscores.std():.3f}")
    except Exception:
        pass

    if save:
        _MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_MODEL_PATH, "wb") as f:
            pickle.dump(pipeline, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.info(f"MisinfoDetector: weights saved to {_MODEL_PATH}")

    return pipeline


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    pipe = build_pipeline(save=True)

    # Quick smoke test
    test_cases = [
        ("TCS Q3 results: net profit up 10% YoY.", 0),
        ("🚀 BUY XYZTECH NOW! 100x guaranteed! Join t.me/pump_group", 1),
        ("SEBI issues clarification on FPI disclosure norms.", 0),
        ("INSIDER TIP: RELIANCE buyback confirmed at 300% premium. Load up!", 1),
    ]
    print("\n=== MisinfoDetector smoke test ===")
    for text, expected in test_cases:
        score = pipe.predict_proba([text])[0][1]
        verdict = "MISINFO" if score > 0.5 else "LEGIT"
        status = "✓" if (score > 0.5) == bool(expected) else "✗"
        print(f"  {status} [{verdict}] score={score:.3f} | {text[:60]}")
    print("==================================\n")
