#!/usr/bin/env python3
"""
Lesson 01 – Combined Demo Runner

Runs existing Lesson 01 demo scripts sequentially.
Each demo is executed twice, in order.

No imports from the demo files.
No refactoring required.
Uses subprocess to preserve known-good behavior.
"""

import subprocess
import time
import sys
from pathlib import Path

# =========================
# Configuration
# =========================

BASE_DIR = Path(__file__).parent
PYTHON = sys.executable  # ensures venv python is used

DEMOS = [
    ("Lissajous Demo", BASE_DIR / "demo_lissajous.py"),
    ("Spiral Demo",    BASE_DIR / "demo_spiral.py"),
]

REPEATS = 2
PAUSE_BETWEEN = 2.0  # seconds

# =========================
# Main
# =========================

def run_demo(name, script_path, pass_num):
    print(f"\n--- {name} (Pass {pass_num}) ---")
    subprocess.run(
        [PYTHON, str(script_path)],
        check=True
    )

def main():
    print("=== Lesson 01 — Combined Demo ===")

    for name, script in DEMOS:
        if not script.exists():
            raise FileNotFoundError(f"Missing demo script: {script}")

        for i in range(REPEATS):
            run_demo(name, script, i + 1)
            time.sleep(PAUSE_BETWEEN)

    print("\nAll demos complete.")

if __name__ == "__main__":
    main()
