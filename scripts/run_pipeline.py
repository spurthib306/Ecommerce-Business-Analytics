"""Run every step in order. Same command on macOS, Windows and Linux:

    python scripts/run_pipeline.py            # all steps
    python scripts/run_pipeline.py --from 3   # start at step 3 (data already cleaned)
    python scripts/run_pipeline.py --only 5   # run a single step
"""
import argparse
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [
    (1, "Download dataset", "01_download_data.py"),
    (2, "Profile and clean data", "02_clean_data.py"),
    (3, "Load database and run SQL", "03_run_sql.py"),
    (4, "Build Excel workbook", "04_build_excel.py"),
    (5, "Build HTML dashboard", "05_build_dashboard.py"),
    (6, "Write insights report", "06_build_report.py"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", type=int, default=1, help="first step to run (1-6)")
    ap.add_argument("--only", type=int, help="run just this step")
    args = ap.parse_args()
    steps = [s for s in STEPS if (s[0] == args.only if args.only else s[0] >= args.start)]
    t0 = time.time()
    for num, label, script in steps:
        print(f"\n=== Step {num}: {label} ===", flush=True)
        rc = subprocess.call([sys.executable, str(HERE / script)], cwd=str(HERE))
        if rc != 0:
            print(f"\nStep {num} failed (exit code {rc}). Fix the message above, then re-run with --from {num}")
            return rc
    print(f"\nAll done in {time.time() - t0:.0f}s. Open PowerBI-Dashboard/dashboard.html in your browser.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
