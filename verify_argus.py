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

print()
print("=" * 56)
print(f"Results: {pass_count} PASSED  |  {fail_count} FAILED")
print("=" * 56)
if fail_count == 0:
    print()
    print("ARGUS is fully operational.")
    print("Run: python demo/run_demo.py --case all")
else:
    sys.exit(1)
