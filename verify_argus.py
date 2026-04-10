"""
verify_argus.py — 10-step ARGUS verification suite.
Run from project root: python verify_argus.py
"""
import os, sys, math, subprocess

# Auto-redirect to venv Python if needed
def _ensure_venv():
    try:
        import torch  # noqa: F401
        return
    except ImportError:
        pass
    root = os.path.dirname(os.path.abspath(__file__))
    venv_py = os.path.join(root, ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_py):
        venv_py = os.path.join(root, ".venv", "bin", "python")
    if os.path.exists(venv_py) and os.path.abspath(sys.executable) != os.path.abspath(venv_py):
        print(f"[ARGUS] Switching to venv: {venv_py}")
        sys.exit(subprocess.run([venv_py, "-W", "ignore"] + sys.argv).returncode)
    elif not os.path.exists(venv_py):
        print("[ARGUS] ERROR: .venv not found.")
        sys.exit(1)

_ensure_venv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

pass_count = 0
fail_count = 0

def check(name, fn):
    global pass_count, fail_count
    try:
        fn()
        print(f"  [PASS] {name}")
        pass_count += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        fail_count += 1

print("=" * 56)
print("ARGUS FULL VERIFICATION SUITE")
print("=" * 56)

# 1. DB
def test_db():
    from data.db.session import engine
    from data.db.models import Base
    Base.metadata.create_all(engine)
check("SQLite DB init + table creation", test_db)

# 2. GNN weights
def test_gnn():
    from models.gnn.train_tcn import load_model
    m = load_model()
    assert m is not None
    assert os.path.exists("models/gnn/tcn_weights.pt")
check("GNN TCN model + trained weights", test_gnn)

# 3. DNA weights
def test_dna():
    from models.dna.autoencoder import get_autoencoder
    ae = get_autoencoder()
    assert ae is not None
    assert os.path.exists("models/dna/autoencoder_weights.pt")
check("DNA Autoencoder + trained weights", test_dna)

# 4. Zero-day detector
def test_zd():
    import numpy as np
    from models.zero_day.anomaly import ZeroDayDetector
    det = ZeroDayDetector()
    X = np.random.rand(20, 25).astype("float32")
    det.fit(X)
    scores = det.score(X[:5])
    assert len(scores) == 5
check("Zero-Day Detector fit+score", test_zd)

# 5. Cross-market fusion
def test_cm():
    from models.cross_market.fusion import CrossMarketFusion
    cm = CrossMarketFusion()
    assert cm is not None
check("Cross-Market Fusion import", test_cm)

# 6. Scoring engine
def test_scoring():
    from scoring.impossibility import compute_poisson_impossibility, compute_composite_score
    s = compute_poisson_impossibility(50, 20, 500, 50)
    assert 0 <= s <= 10
    c = compute_composite_score(8.0, 7.0, 6.0, 5.0)
    assert 0 <= c <= 10
check("Impossibility + composite scoring", test_scoring)

# 7. PDF generation
def test_pdf():
    import uuid
    from datetime import datetime
    from data.db.session import get_session
    from data.db.models import Alert, SEBICase
    from reports.pdf_generator import generate_case_pdf
    db = get_session()
    alert = Alert(
        id=str(uuid.uuid4()), scrip="VTEST", exchange="NSE",
        detected_at=datetime.now(), impossibility_score=8.5,
        scheme_type="pump_and_dump", accounts_involved=["A1", "A2"],
        gnn_score=9.0, dna_score=7.0, cross_market_score=6.0,
        zero_day_score=8.0, status="open",
    )
    db.add(alert); db.commit(); db.refresh(alert)
    case = SEBICase(
        id=str(uuid.uuid4()), alert_id=alert.id,
        case_number=f"VERIFY/{uuid.uuid4().hex[:6].upper()}",
        entity_names=["TEST ENTITY"], scrip="VTEST",
        from_date=datetime.now().date(), to_date=datetime.now().date(),
        estimated_gain=100000.0, evidence_json={}, status="draft",
    )
    db.add(case); db.commit()
    out = "verify_test.pdf"
    generate_case_pdf(alert, case, out)
    assert os.path.getsize(out) > 1000
    os.remove(out)
    db.close()
check("SEBI PDF report generation", test_pdf)

# 8. FastAPI app import
def test_api():
    from api.main import app
    assert app is not None
check("FastAPI app import", test_api)

# 9. AlertEngine (no Redis required)
def test_alert_engine():
    from scoring.alert_engine import AlertEngine
    from data.db.session import get_session
    db = get_session()
    ae = AlertEngine(session=db)   # redis_client=None by default
    assert ae is not None
    db.close()
check("AlertEngine init (no Redis)", test_alert_engine)

# 10. Demo pump_and_dump run_detection()
def test_demo():
    from demo.real_cases.case_pump_dump import run_detection
    result = run_detection()
    assert result.get("overall_score") is not None
    assert not math.isnan(result["overall_score"])
    assert result["scheme_type"] == "pump_and_dump"
check("Demo: pump_and_dump run_detection()", test_demo)

# 11. MitigationEngine import + recommend() sanity check
def test_mitigation_recommend():
    from scoring.mitigation_engine import MitigationEngine
    me = MitigationEngine()
    result = me.recommend(
        alert_score=9.1,
        threat_type="market_manipulation",
        scheme_type="pump_and_dump",
        gnn_score=8.5,
        dna_score=7.9,
        zero_day_score=8.8,
        social_signal_score=0.75,
        misinfo_score=0.6,
    )
    assert result["recommended_action"] is not None, "recommended_action is None"
    assert result["severity"] in ("low", "medium", "high", "critical"), f"Bad severity: {result['severity']}"
    assert result["severity"] == "critical", f"Expected critical for score 9.1, got {result['severity']}"
    assert result["recommended_action"] == "freeze_accounts_and_escalate_sebi"
    assert result["escalate_to_sebi"] is True
    assert result["auto_mitigate"] is True  # critical + pump_and_dump
check("MitigationEngine recommend() logic", test_mitigation_recommend)

# 12. MitigationEngine apply/dismiss/escalate with in-memory SQLite
def test_mitigation_crud():
    import uuid
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from data.db.models import Base, Alert
    from datetime import datetime
    from scoring.mitigation_engine import MitigationEngine

    engine_mem = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine_mem)
    Session = sessionmaker(bind=engine_mem)
    db = Session()

    alert_id = str(uuid.uuid4())
    alert = Alert(
        id=alert_id, scrip="TEST_SCRIP", exchange="NSE",
        detected_at=datetime.utcnow(), impossibility_score=8.5,
        scheme_type="spoofing",
        accounts_involved="[]",
        gnn_score=8.0, dna_score=7.0,
        cross_market_score=5.0, zero_day_score=8.1,
    )
    db.add(alert)
    db.commit()

    me = MitigationEngine()
    # apply
    updated = me.apply(db, alert_id, "freeze_accounts_pending_review", "test_analyst", "test notes")
    assert updated.mitigation_status == "applied"
    assert updated.mitigation_applied_by == "test_analyst"
    # dismiss
    updated = me.dismiss(db, alert_id, "test_analyst", "false positive")
    assert updated.mitigation_status == "dismissed"
    # escalate
    updated = me.escalate(db, alert_id, "test_analyst")
    assert updated.mitigation_status == "escalated"
    assert updated.escalated_to_sebi is True
    db.close()
check("MitigationEngine apply/dismiss/escalate (in-memory DB)", test_mitigation_crud)

# 13. Mitigation summary endpoint importable
def test_mitigation_endpoint():
    from api.routers.alerts import router
    routes = [r.path for r in router.routes]
    assert any("mitigation/summary" in p for p in routes), f"Mitigation summary not found in routes: {routes}"
    assert any("mitigate" in p for p in routes), f"Mitigate endpoint not found in routes: {routes}"
    assert any("escalate" in p for p in routes), f"Escalate endpoint not found in routes: {routes}"
check("Mitigation endpoints registered on router", test_mitigation_endpoint)

# 14. AlertOut schema has mitigation fields
def test_mitigation_schema():
    from api.schemas import AlertOut, MitigationSummaryOut, MitigationApplyRequest
    fields = AlertOut.model_fields
    for f in ("recommended_action", "mitigation_status", "severity", "escalated_to_sebi", "auto_mitigated"):
        assert f in fields, f"AlertOut missing field: {f}"
    assert "pending_mitigation" in MitigationSummaryOut.model_fields
    assert "action" in MitigationApplyRequest.model_fields
check("AlertOut + Mitigation schemas have all required fields", test_mitigation_schema)

# 15. Social signal fetcher — smoke test against XYZTECH
def test_social_signal():
    from data.ingest.social_signal_fetcher import _score_manipulation, get_social_score_for_scrip
    # Direct scoring without hitting Reddit API
    score_01 = _score_manipulation(
        "XYZTECH guaranteed 500% returns! Operator call confirmed. Buy NOW! t.me/pump circuit target"
    )
    assert isinstance(score_01, float), f"Expected float, got {type(score_01)}"
    assert 0.0 <= score_01 <= 1.0, f"Score {score_01} out of [0,1] range"
    assert score_01 > 0.3, f"Expected pump text to score >0.3, got {score_01}"
    # Verify [0,10] scale conversion
    score_scaled = round(min(10.0, score_01 * 10.0), 3)
    assert 0.0 <= score_scaled <= 10.0
check("Social signal fetcher — pump text scoring", test_social_signal)

# 16. Misinfo detector — model load + inference
def test_misinfo_detector():
    from models.misinfo.detector import detect
    manipulative_text = "SEBI has approved guaranteed 500% returns on XYZTECH. Buy now, risk-free! Sure shot multibagger confirmed."
    score = detect(manipulative_text)
    assert isinstance(score, float), f"Expected float, got {type(score)}"
    assert 0.0 <= score <= 1.0, f"Score {score} out of [0,1] range"
    assert score > 0.5, f"Expected high misinfo score on manipulative text, got {score}"
    neutral_text = "XYZTECH reported Q3 results in line with analyst estimates."
    neutral_score = detect(neutral_text)
    assert isinstance(neutral_score, float)
    assert neutral_score < score, "Neutral text should score lower than manipulative text"
check("Misinfo detector — load weights + inference", test_misinfo_detector)

# 17. Generic threat adapter — phishing URL normalization
def test_generic_adapter():
    from data.ingest.generic_threat_adapter import normalize
    result = normalize(
        "http://nse1ndia-login.xyz/verify?token=abc&redirect=account-suspended",
        platform="web",
        entity_id="test_entity",
    )
    required_keys = {"entity_id", "timestamp", "threat_type", "platform", "raw_signal", "threat_score"}
    missing = required_keys - set(result.keys())
    assert not missing, f"Missing keys in result: {missing}"
    assert result["threat_type"] == "phishing", f"Expected phishing, got {result['threat_type']}"
    assert result["threat_score"] > 0.0, f"Phishing score should be > 0, got {result['threat_score']}"
    assert result["platform"] == "web"
    assert result["entity_id"] == "test_entity"
    # Batch test
    from data.ingest.generic_threat_adapter import normalize_batch
    batch = normalize_batch([
        "http://nse1ndia-login.xyz/verify",
        {"action": "mass_message", "bulk_action": True, "is_automated": True},
        "guaranteed profit buy now XYZTECH to the moon operator call",
    ])
    assert len(batch) == 3
    assert all("threat_score" in r for r in batch)
check("Generic threat adapter — normalize() + normalize_batch()", test_generic_adapter)

print()
print("=" * 56)
print(f"Results: {pass_count} PASSED  |  {fail_count} FAILED")
print("=" * 56)
if fail_count == 0:
    print()
    print("ARGUS is fully operational. 17/17 verified.")
    print("Run: python demo/run_demo.py --case all")
else:
    sys.exit(1)
