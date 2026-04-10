"""Quick validation of GNN inference speed and score quality."""
import sys, time
sys.path.insert(0, '.')

from demo.real_cases.case_pump_dump import generate_pump_dump_trades
from models.gnn.train_tcn import load_model, run_inference

print("Step 1: Generate trades...")
df = generate_pump_dump_trades()
print(f"  {len(df)} rows  |  {df['account_id'].nunique()} accounts")

print("Step 2: Load model...")
model = load_model()

print("Step 3: GNN inference (demo_mode=True)...")
t0 = time.time()
gnn = run_inference(model, df, demo_mode=True)
elapsed = time.time() - t0
print(f"  Elapsed : {elapsed:.2f}s")
print(f"  GNN score       : {gnn['gnn_score']}")
print(f"  Flagged accounts: {len(gnn['flagged_accounts'])}")

colluding = set(df[df["is_manipulated"]]["account_id"].unique())
flagged   = set(gnn["flagged_accounts"])
tp = len(flagged & colluding)
fp = len(flagged - colluding)
print(f"  TP: {tp}/{len(colluding)}   FP: {fp}")

score_ok  = gnn["gnn_score"] >= 7.0
speed_ok  = elapsed < 10.0
print()
if score_ok and speed_ok:
    print("PASS — GNN fast and high-scoring")
else:
    if not score_ok:
        print(f"WARN  — score {gnn['gnn_score']} < 7.0")
    if not speed_ok:
        print(f"WARN  — elapsed {elapsed:.1f}s > 10s limit")
