"""Step 1 - download the Olist dataset from Kaggle into Dataset/raw.

Uses kagglehub, which downloads public datasets without an API key.
If the download fails (no internet, Kaggle changes), download the zip
manually from the URL printed below and extract the CSVs into Dataset/raw.
The raw files are never modified; later steps work on copies.
"""
import os
import shutil
import sys

from config import KAGGLE_CACHE, KAGGLE_DATASET, KAGGLE_URL, RAW_DIR, RAW_FILES, ensure_dirs


def missing_files():
    return [f for f in RAW_FILES if not (RAW_DIR / f).exists()]


def main():
    ensure_dirs()
    if not missing_files():
        print(f"[download] All {len(RAW_FILES)} raw files already present in {RAW_DIR}")
        return 0

    # kagglehub reads its cache location from this env var at import time.
    os.environ["KAGGLEHUB_CACHE"] = str(KAGGLE_CACHE)
    try:
        import kagglehub
        src = kagglehub.dataset_download(KAGGLE_DATASET)
    except Exception as exc:  # network or Kaggle API problem
        print(f"[download] Automatic download failed: {exc}")
        print(f"[download] Download manually from {KAGGLE_URL}")
        print(f"[download] and extract the CSV files into: {RAW_DIR}")
        return 1

    from pathlib import Path
    for name in RAW_FILES:
        found = list(Path(src).rglob(name))
        if found:
            shutil.copy2(found[0], RAW_DIR / name)
    still_missing = missing_files()
    if still_missing:
        print(f"[download] Missing after download: {still_missing}")
        return 1
    shutil.rmtree(KAGGLE_CACHE, ignore_errors=True)
    print(f"[download] Saved {len(RAW_FILES)} files to {RAW_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
