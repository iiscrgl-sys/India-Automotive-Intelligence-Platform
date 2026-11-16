"""
Builds IAIP\\deploy\\ : everything Streamlit Community Cloud needs, ready to drag into GitHub.
Run with make_deploy.bat (or: python make_deploy.py from the dashboard folder).
Re-run it after every refresh (e.g. Demo B), then upload the deploy folder to GitHub again.
"""
import shutil
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent          # IAIP\dashboard
BASE = HERE.parent                              # IAIP
WH = BASE / "warehouse"
OUT = BASE / "deploy"

TABLES = {
    "gold": ["state_month_registrations", "ev_share_state_month", "fuel_mix_trend", "emission_transition",
             "category_growth", "brand_share_year", "state_safety_profile", "state_profile_latest",
             "dim_state", "dim_maker", "fact_registration_maker_year",
             "ml_ev_forecast_test", "ml_ev_forecast_future", "ml_model_comparison", "ml_state_groups", "_gold_checks"],
    "silver": ["_quality_report"],
    "stream": ["_stream_checks", "_stream_log"],
}

if OUT.exists():
    shutil.rmtree(OUT)
total = 0
for folder, names in TABLES.items():
    (OUT / "data" / folder).mkdir(parents=True, exist_ok=True)
    for name in names:
        src = WH / folder / name
        if not src.exists():
            print(f"  skipped (not found): {folder}/{name}")
            continue
        df = pd.read_parquet(src)
        for c in df.columns:                                   # partition columns come back as 'category'
            if str(df[c].dtype) == "category":
                df[c] = df[c].astype(str)
        dst = OUT / "data" / folder / f"{name}.parquet"
        df.to_parquet(dst, index=False)
        total += dst.stat().st_size
        print(f"  data/{folder}/{name}.parquet  {len(df):>7,} rows  {dst.stat().st_size/1e6:5.2f} MB")

(OUT / "data" / "reports").mkdir(parents=True, exist_ok=True)
for f in ["e1_scalability.csv", "e3_quality_test.csv"]:
    if (BASE / "reports" / f).exists():
        shutil.copy2(BASE / "reports" / f, OUT / "data" / "reports" / f)

for f in ["app.py", "requirements.txt", "README.md"]:
    shutil.copy2(HERE / f, OUT / f)
if (HERE / ".streamlit" / "config.toml").exists():          # optional theme file
    (OUT / ".streamlit").mkdir(exist_ok=True)
    shutil.copy2(HERE / ".streamlit" / "config.toml", OUT / ".streamlit" / "config.toml")

n_files = sum(1 for p in OUT.rglob("*") if p.is_file())
print(f"\nDeploy folder ready: {OUT}")
print(f"{n_files} files, {total/1e6:.1f} MB of data. Next: upload the CONTENTS of this folder to GitHub.")
