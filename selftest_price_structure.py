#!/usr/bin/env python3
"""Network-free smoke test for the structure engine."""
import json
import numpy as np
import pandas as pd

from price_structure_engine import analyze_stock

rng = np.random.default_rng(7)
n = 220
idx = pd.bdate_range("2025-09-01", periods=n)
base = 100 + np.linspace(0, 18, n) + np.sin(np.linspace(0, 16, n))*3
noise = rng.normal(0, 0.7, n)
close = base + noise
open_ = close + rng.normal(0, .5, n)
high = np.maximum(open_, close) + rng.uniform(.3, 1.3, n)
low = np.minimum(open_, close) - rng.uniform(.3, 1.3, n)
vol = rng.integers(500_000, 2_000_000, n)
df = pd.DataFrame({"Open":open_,"High":high,"Low":low,"Close":close,"Volume":vol}, index=idx)
bench = pd.DataFrame({"Open":base,"High":base+1,"Low":base-1,"Close":base,"Volume":vol}, index=idx)
cfg = json.load(open("price_structure_config.json", encoding="utf-8"))
r = analyze_stock(df, bench, cfg)
assert 0 <= r["score"] <= 100
assert r["grade"] in {"A+","A","B","C","D"}
assert "chart" in r and len(r["chart"]["bars"]) > 50
print("SELFTEST OK", r["grade"], r["score"], r["setup"])
