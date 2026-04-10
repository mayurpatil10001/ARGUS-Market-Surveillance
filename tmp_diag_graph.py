"""Diagnose edge building in build_trade_graph."""
import sys
sys.path.insert(0, '.')
import pandas as pd, numpy as np
from demo.real_cases.case_pump_dump import generate_pump_dump_trades
from models.gnn.tcn import build_trade_graph

df = generate_pump_dump_trades()
colluding = set(df[df["is_manipulated"]]["account_id"].unique())
print(f"Total rows: {len(df)}, Colluding rows: {df['is_manipulated'].sum()}")

# Check time spread of colluding trades within a single coordination event
col_df = df[df["is_manipulated"]].copy()
col_df["ts_ms"] = pd.to_datetime(col_df["timestamp"]).astype("int64") // 1_000_000
# Group by approximate time bucket (round to nearest second)
col_df["bucket"] = col_df["ts_ms"] // 30000  # 30-second buckets
bucket_counts = col_df.groupby("bucket").size()
print(f"Colluding buckets (30s): {len(bucket_counts)}, max per bucket: {bucket_counts.max()}")

# Check time spread within a bucket
sample_bucket = bucket_counts.idxmax()
bucket_trades = col_df[col_df["bucket"] == sample_bucket]
ts_vals = bucket_trades["ts_ms"].values
print(f"Sample bucket time spread: {ts_vals.max() - ts_vals.min()} ms over {len(bucket_trades)} trades")

# Try with window_ms=200
g = build_trade_graph(df, window_ms=200, min_coincidences=1)
print(f"Graph: {g.num_nodes} nodes, {g.edge_index.shape[1]//2} undirected edges")

# Try on colluding-only subset  
g2 = build_trade_graph(col_df, window_ms=200, min_coincidences=1)
print(f"Colluding-only graph: {g2.num_nodes} nodes, {g2.edge_index.shape[1]//2} edges")
